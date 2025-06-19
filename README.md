
# Acquia DAM to HubSpot Sync (AWS Lambda)

This AWS Lambda function syncs digital assets from Acquia DAM to HubSpot File Manager.

## 📦 Features
- Pulls assets from Acquia DAM via its API.
- Uploads new assets to HubSpot File Manager.
- Maintains state to avoid duplicates.
- Uses environment variables for secrets.
- Logs sync details for auditability.

---

## ⚙️ Prerequisites

- AWS CLI and credentials configured.
- HubSpot API Access Token.
- Acquia DAM API Key.
- IAM Role with Lambda and SSM/DynamoDB permissions.
- Python 3.9+ environment.

---

## 📁 Directory Structure

```
acquia-dam-to-hubspot-sync/
│
├── scripts/
│   └── lambda_function.py
├── requirements.txt
└── README.md
```

---

## 📥 Install Dependencies Locally (for packaging)

```bash
pip install -r requirements.txt -t ./package
cp -r scripts/* ./package/
cd package
zip -r ../acquia-dam-to-hubspot-sync.zip .
```

---

## 🚀 Deploy to AWS Lambda

```bash
aws lambda create-function \
  --function-name acquiaHubspotSync \
  --runtime python3.9 \
  --role arn:aws:iam::<account-id>:role/<lambda-execution-role> \
  --handler acquia_to_hubspot_lambda.lambda_handler \
  --timeout 300 \
  --memory-size 512 \
  --zip-file fileb://acquia-dam-to-hubspot-sync.zip \
  --environment Variables={ACQUIA_DAM_API_KEY="your_token",HUBSPOT_ACCESS_TOKEN="your_token"}
```

---

## 📅 Schedule with EventBridge

```bash
aws events put-rule \
  --schedule-expression "rate(1 hour)" \
  --name AcquiaHubspotHourlyRule

aws lambda add-permission \
  --function-name acquiaHubspotSync \
  --statement-id AcquiaEventInvoke \
  --action 'lambda:InvokeFunction' \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<region>:<account-id>:rule/AcquiaHubspotHourlyRule

aws events put-targets \
  --rule AcquiaHubspotHourlyRule \
  --targets "Id"="1","Arn"="arn:aws:lambda:<region>:<account-id>:function:acquiaHubspotSync"
```

---

## ✅ Test the Lambda

```bash
aws lambda invoke \
  --function-name acquiaHubspotSync \
  --payload '{}' \
  response.json
```

---

## 📌 Notes

- Store secrets securely using AWS Secrets Manager or SSM Parameter Store.
- Consider using versioning and aliases for safe deployments.
- Review IAM permissions before production deployment.

---

## 📬 Support

Raise issues or contact the author if integration problems arise.
