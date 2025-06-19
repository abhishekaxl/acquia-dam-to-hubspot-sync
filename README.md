# Acquia DAM to HubSpot Sync – AWS Lambda

This project syncs assets from Acquia DAM to HubSpot File Manager using an AWS Lambda function.

## 🛠 Prerequisites

- AWS CLI configured with IAM permissions to deploy Lambda and EventBridge.
- Python 3.9 or higher
- Acquia DAM API Token
- HubSpot Private App Access Token

## 📁 Project Structure

```
.
├── scripts/
│   └── acquia_to_hubspot_lambda.py   # Lambda function
└── README.md                         # Deployment instructions
```

## 🚀 Deployment Steps

### 1. Package the Lambda

```bash
cd scripts
zip ../function.zip acquia_to_hubspot_lambda.py
```

### 2. Create Lambda Function

```bash
aws lambda create-function \
  --function-name acquiaHubspotSync \
  --runtime python3.12 \
  --role arn:aws:iam::<your-account-id>:role/LAMBDAADMIN \
  --handler acquia_to_hubspot_lambda.lambda_handler \
  --zip-file fileb://function.zip \
  --environment Variables="{ACQUIA_DAM_API_KEY='...', HUBSPOT_ACCESS_TOKEN='...'}"
```

### 3. Add Permissions (optional for EventBridge)

```bash
aws lambda add-permission \
  --function-name acquiaHubspotSync \
  --statement-id lambda-eventbridge \
  --action 'lambda:InvokeFunction' \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<region>:<account-id>:rule/AcquiaSyncScheduler
```

### 4. Create Scheduled Event (Every 15 mins)

```bash
aws events put-rule \
  --name AcquiaSyncScheduler \
  --schedule-expression 'rate(15 minutes)'
```

```bash
aws events put-targets \
  --rule AcquiaSyncScheduler \
  --targets 'Id'='1','Arn'='arn:aws:lambda:<region>:<account-id>:function:acquiaHubspotSync'
```

## ✅ Manual Test

```bash
aws lambda invoke \
  --function-name acquiaHubspotSync \
  --payload '{}' \
  response.json
cat response.json
```

## 📊 Logs

```bash
aws logs describe-log-groups
aws logs describe-log-streams --log-group-name /aws/lambda/acquiaHubspotSync
```

---

Feel free to raise issues or contribute!
