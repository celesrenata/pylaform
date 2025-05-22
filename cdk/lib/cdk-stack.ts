import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as path from 'path';
import * as certificatemanager from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

export class PylaformAmazonQStack extends cdk.Stack {
  public readonly aiServiceLambda: lambda.Function;
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create DynamoDB table with a Global Secondary Index
    const dataTable = new dynamodb.Table(this, 'PylaformDataTable', {
      tableName: 'pylaform-data',
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN, // RETAIN for production, DESTROY for dev
      pointInTimeRecovery: true
    });

    // Add Global Secondary Index for parent-child relationships
    dataTable.addGlobalSecondaryIndex({
      indexName: 'GSI1',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },
    });

    dataTable.addGlobalSecondaryIndex({
      indexName: 'EmailIndex',
      partitionKey: { name: 'email', type: dynamodb.AttributeType.STRING },
      // No sortKey needed unless you want to support multiple users per email
    });

    // Create or import a VPC for the Lambda function
    const vpc = new ec2.Vpc(this, 'PylaformVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          name: 'private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        }
      ]
    });

    // Create IAM role for Lambda
    const lambdaRole = new iam.Role(this, 'PylaformLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
      ],
    });

    // Grant DynamoDB access
    dataTable.grantReadWriteData(lambdaRole);

    // Add Amazon Q permissions
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'qbusiness:StartConversation',
        'qbusiness:SendMessage',
        'qbusiness:GetConversation',
        'qbusiness:ListMessages',
        'qbusiness:ListApplications',
        'qbusiness:GetApplication',
      ],
      resources: ['*'], // For production, restrict this to specific resources
    }));

    const lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
      vpc: vpc,
      description: 'Security group for Lambda functions',
      allowAllOutbound: false, // We'll define specific outbound rules
    });

    // Allow outbound SMTP traffic to Google's SMTP servers
    lambdaSecurityGroup.addEgressRule(
      ec2.Peer.ipv4('0.0.0.0/0'), // You can restrict this to Google's IP ranges for better security
      ec2.Port.tcp(587),
      'Allow outbound SMTP over TLS'
    );

    // Allow HTTPS outbound for other API calls
    lambdaSecurityGroup.addEgressRule(
      ec2.Peer.ipv4('0.0.0.0/0'),
      ec2.Port.tcp(443),
      'Allow outbound HTTPS'
    );

    // Import or create the email configuration secret
    const emailConfigSecret = secretsmanager.Secret.fromSecretNameV2(
        this,
        'EmailConfigSecret',
        'pylaform/email-config'
    );

    // Update the lambda layer path for Python 3.11
    const dependenciesLayer = new lambda.LayerVersion(this, 'PylaformDependencies', {
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda-layer/python'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            [
              'pip install -r requirements.txt -t /asset-output/python/lib/python3.11/site-packages'
            ].join(' && ')
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Python dependencies for Pylaform',
    });

    // Add at the top of the constructor, before aiServiceLambda
    const amazonQApplicationId = new cdk.CfnParameter(this, 'AmazonQApplicationId', {
      type: 'String',
      description: 'The Amazon Q Application ID',
    });

    const aiServiceLambda = new lambda.Function(this, 'PylaformAIService', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda_build')),
      layers: [dependenciesLayer],
      vpc: vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS
      },
      securityGroups: [lambdaSecurityGroup],
      environment: {
        'AI_SERVICE_TYPE': 'AMAZON_Q',
        'AMAZON_Q_REGION': this.region,
        'AMAZON_Q_APPLICATION_ID': amazonQApplicationId.valueAsString,
        'DYNAMODB_TABLE_NAME': dataTable.tableName,
        'EMAIL_CONFIG_SECRET_NAME': 'pylaform/email-config',
      },
      timeout: cdk.Duration.seconds(30),
      memorySize: 128,
      role: lambdaRole,
    });

    // Grant Lambda permission to read the secrets from Secrets Manager
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: [
        // Grant access to both secrets
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:pylaform/flask-secret*`,
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:pylaform/email-config*`
      ],
    }));

    // Grant access to the email config secret specifically
    emailConfigSecret.grantRead(aiServiceLambda);

    this.aiServiceLambda = aiServiceLambda;

    const lambdaLogGroup = logs.LogGroup.fromLogGroupName(
      this,
      'ImportedPylaformLambdaLogGroup',
      `/aws/lambda/${aiServiceLambda.functionName}`
    );

    // Create API Gateway
    const api = new apigateway.RestApi(this, 'PylaformAPI', {
      restApiName: 'Pylaform Resume Service',
      description: 'API for Pylaform Resume Service with Amazon Q integration',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
      },
    });

    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, 'PylaformHostedZone', {
      hostedZoneId: 'Z2ASM5FKNQBRT2',
      zoneName: 'celestium.life',
    });

    // Create an ACM certificate in us-east-1 for API Gateway custom domain
    const certificate = new certificatemanager.DnsValidatedCertificate(this, 'PylaformAPICertificate', {
      domainName: 'pylaform.celestium.life',
      hostedZone,
      region: 'us-west-2', // API Gateway requires certs in us-east-1
    });

    // Create the custom domain for API Gateway
    const customDomain = new apigateway.DomainName(this, 'PylaformCustomDomain', {
      domainName: 'pylaform.celestium.life',
      certificate,
      endpointType: apigateway.EndpointType.REGIONAL,
      securityPolicy: apigateway.SecurityPolicy.TLS_1_2,
    });

    // Map the custom domain to the API stage
    new apigateway.BasePathMapping(this, 'PylaformBasePathMapping', {
      domainName: customDomain,
      restApi: api,
      basePath: '', // root
    });

    // Create a Route53 alias record for the custom domain
    new route53.ARecord(this, 'PylaformAPIAliasRecord', {
      zone: hostedZone,
      recordName: 'pylaform',
      target: route53.RecordTarget.fromAlias(new targets.ApiGatewayDomain(customDomain)),
    });

    // Add Lambda as integration
    const aiServiceIntegration = new apigateway.LambdaIntegration(aiServiceLambda);

    // Add routes
    api.root.addMethod('ANY', aiServiceIntegration);

    // Add proxy resource to handle all paths
    const proxy = api.root.addResource('{proxy+}');
    proxy.addMethod('ANY', aiServiceIntegration);

    // Output the API URL
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'URL of the Pylaform API',
    });

    // Output the DynamoDB table name
    new cdk.CfnOutput(this, 'DynamoDBTableName', {
      value: dataTable.tableName,
      description: 'Name of the Pylaform DynamoDB table',
    });

    new cdk.CfnOutput(this, 'PylaformAIServiceLambdaArn', {
      value: aiServiceLambda.functionArn,
      description: 'ARN of the Pylaform AI Service Lambda function',
      exportName: 'PylaformAIServiceLambdaArn', // Enables cross-stack reference
    });
  }
}