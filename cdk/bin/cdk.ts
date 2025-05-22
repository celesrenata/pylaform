import * as cdk from 'aws-cdk-lib';
import { PylaformAmazonQStack } from '../lib/cdk-stack';
import { MonitoringStack } from '../lib/monitoring-stack';

const app = new cdk.App();

const mainStack = new PylaformAmazonQStack(app, 'PylaformAmazonQStack', {
  /* any required props */
});

// Import the Lambda function name output from the main stack
const lambdaFunctionName = mainStack.aiServiceLambda.functionName;

new MonitoringStack(app, 'MonitoringStack', {
  lambdaFunctionName: lambdaFunctionName,
  notificationEmail: 'celes@celestium.life',
});
