import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatch_actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';

export interface MonitoringStackProps extends cdk.StackProps {
  lambdaFunctionName: string;
  notificationEmail: string;
}

export class MonitoringStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    // Import the existing Lambda function by name
    const aiServiceLambda = lambda.Function.fromFunctionName(
      this,
      'ImportedPylaformAIService',
      props.lambdaFunctionName
    );

    // Import the corresponding CloudWatch Log Group
    const lambdaLogGroup = logs.LogGroup.fromLogGroupName(
      this,
      'ImportedPylaformLambdaLogGroup',
      `/aws/lambda/${props.lambdaFunctionName}`
    );

    // SNS Topic for alarm notifications
    const errorAlarmTopic = new sns.Topic(this, 'PylaformLambdaErrorAlarmTopic', {
      displayName: 'Pylaform Lambda Error Alarm Topic',
    });
    errorAlarmTopic.addSubscription(
      new subscriptions.EmailSubscription(props.notificationEmail)
    );

    // Additional metrics for email verification and registration
    const emailVerificationMetric = new logs.MetricFilter(this, 'EmailVerificationMetric', {
      logGroup: lambdaLogGroup,
      metricNamespace: 'Pylaform',
      metricName: 'EmailVerification',
      filterPattern: logs.FilterPattern.literal('INFO Verification email sent'),
      metricValue: '1',
      defaultValue: 0,
    });

    const userRegistrationMetric = new logs.MetricFilter(this, 'UserRegistrationMetric', {
      logGroup: lambdaLogGroup,
      metricNamespace: 'Pylaform',
      metricName: 'UserRegistration',
      filterPattern: logs.FilterPattern.literal('INFO New user registered'),
      metricValue: '1',
      defaultValue: 0,
    });

    // Throttling metric - useful to detect if your Lambda is being throttled
    const throttlingMetric = new logs.MetricFilter(this, 'ThrottlingMetric', {
      logGroup: lambdaLogGroup,
      metricNamespace: 'Pylaform',
      metricName: 'LambdaThrottling',
      filterPattern: logs.FilterPattern.literal('Task timed out'),
      metricValue: '1',
      defaultValue: 0,
    });

    // Alarm for throttling
    const throttlingAlarm = new cloudwatch.Alarm(this, 'ThrottlingAlarm', {
      metric: new cloudwatch.Metric({
        namespace: 'Pylaform',
        metricName: 'LambdaThrottling',
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 1,
      datapointsToAlarm: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: 'Alarm if the Lambda function is being throttled',
    });
    throttlingAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(errorAlarmTopic));

    // Alarm for Lambda errors
    const lambdaErrorAlarm = new cloudwatch.Alarm(this, 'PylaformLambdaErrorAlarm', {
      metric: aiServiceLambda.metricErrors(),
      threshold: 1,
      evaluationPeriods: 1,
      datapointsToAlarm: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: 'Alarm if the Lambda function has any errors',
    });
    lambdaErrorAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(errorAlarmTopic));

    // Create log-based metrics for email tracking

    // 1. Email Sent Success Metric
    const emailSentMetric = new logs.MetricFilter(this, 'EmailSentSuccessMetric', {
      logGroup: lambdaLogGroup,
      metricNamespace: 'Pylaform',
      metricName: 'EmailSentSuccess',
      filterPattern: logs.FilterPattern.literal('INFO Email sent successfully'),
      metricValue: '1',
      defaultValue: 0,
    });

    // 2. Email Failure Metric
    const emailFailureMetric = new logs.MetricFilter(this, 'EmailFailureMetric', {
      logGroup: lambdaLogGroup,
      metricNamespace: 'Pylaform',
      metricName: 'EmailSendFailure',
      filterPattern: logs.FilterPattern.literal('ERROR Failed to send email'),
      metricValue: '1',
      defaultValue: 0,
    });

    // 3. Email Configuration Error Metric
    const emailConfigErrorMetric = new logs.MetricFilter(this, 'EmailConfigErrorMetric', {
      logGroup: lambdaLogGroup,
      metricNamespace: 'Pylaform',
      metricName: 'EmailConfigError',
      filterPattern: logs.FilterPattern.literal('ERROR Error getting email configuration'),
      metricValue: '1',
      defaultValue: 0,
    });

    // Create alarms for email metrics

    // Alarm for email failures
    const emailFailureAlarm = new cloudwatch.Alarm(this, 'EmailFailureAlarm', {
      metric: new cloudwatch.Metric({
        namespace: 'Pylaform',
        metricName: 'EmailSendFailure',
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 1,
      datapointsToAlarm: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: 'Alarm if any emails fail to send',
    });
    emailFailureAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(errorAlarmTopic));

    // Alarm for email configuration errors
    const emailConfigErrorAlarm = new cloudwatch.Alarm(this, 'EmailConfigErrorAlarm', {
      metric: new cloudwatch.Metric({
        namespace: 'Pylaform',
        metricName: 'EmailConfigError',
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 1,
      datapointsToAlarm: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: 'Alarm if there are any email configuration errors',
    });
    emailConfigErrorAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(errorAlarmTopic));

    // Dashboard for Lambda metrics and logs
    const dashboard = new cloudwatch.Dashboard(this, 'PylaformDashboard', {
      dashboardName: 'PylaformAppDashboard',
    });

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Invocations',
        left: [aiServiceLambda.metricInvocations()],
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Errors',
        left: [aiServiceLambda.metricErrors()],
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Duration',
        left: [aiServiceLambda.metricDuration()],
      }),

      // Add email metrics to dashboard
      new cloudwatch.GraphWidget({
        title: 'Email Metrics',
        left: [
          new cloudwatch.Metric({
            namespace: 'Pylaform',
            metricName: 'EmailSentSuccess',
            statistic: 'Sum',
            period: cdk.Duration.minutes(5),
            label: 'Emails Sent Successfully'
          }),
          new cloudwatch.Metric({
            namespace: 'Pylaform',
            metricName: 'EmailSendFailure',
            statistic: 'Sum',
            period: cdk.Duration.minutes(5),
            label: 'Email Send Failures'
          }),
          new cloudwatch.Metric({
            namespace: 'Pylaform',
            metricName: 'EmailConfigError',
            statistic: 'Sum',
            period: cdk.Duration.minutes(5),
            label: 'Email Config Errors'
          })
        ],
        width: 24,
        height: 6,
      }),

      new cloudwatch.GraphWidget({
        title: 'Email Success Rate',
        left: [
          new cloudwatch.MathExpression({
            expression: '100 * m1 / (m1 + m2)',
            label: 'Email Success Rate (%)',
            usingMetrics: {
              m1: new cloudwatch.Metric({
                namespace: 'Pylaform',
                metricName: 'EmailSentSuccess',
                statistic: 'Sum',
                period: cdk.Duration.minutes(60),
              }),
              m2: new cloudwatch.Metric({
                namespace: 'Pylaform',
                metricName: 'EmailSendFailure',
                statistic: 'Sum',
                period: cdk.Duration.minutes(60),
              })
            }
          })
        ],
        width: 24,
        height: 6,
      }),

      // Add email-specific log query widget
      new cloudwatch.LogQueryWidget({
        title: 'Recent Email Activity',
        logGroupNames: [lambdaLogGroup.logGroupName],
        view: cloudwatch.LogQueryVisualizationType.TABLE,
        queryLines: [
          'fields @timestamp, @message',
          'filter @message like /Email/ or @message like /email/ or @message like /SMTP/',
          'sort @timestamp desc',
          'limit 20'
        ],
        width: 24,
        height: 6,
      }),

      new cloudwatch.LogQueryWidget({
        title: 'Recent Lambda Logs',
        logGroupNames: [lambdaLogGroup.logGroupName],
        view: cloudwatch.LogQueryVisualizationType.TABLE,
        queryLines: [
          'fields @timestamp, @message',
          'sort @timestamp desc',
          'limit 20'
        ],
        width: 24,
        height: 6,
      })
    );
  }
}