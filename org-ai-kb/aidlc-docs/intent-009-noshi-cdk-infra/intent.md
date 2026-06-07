# Intent — noshi CDK infra (N4 tech-hardening)

## Prompt
design-review-002 N4 の技術ハードニング。infrastructure-design（intent-002）を AWS CDK の実 IaC として実装し、cdk synth で検証したい。brownfield。

## Summary
intent-002 の infrastructure-design.md / deployment-architecture.md を、AWS CDK(TypeScript) の実コードに落とす。DataStack(DynamoDB/S3/KMS, PITR/TTL/GSI, 削除保護)・MessagingStack(SQS+DLQ)・ApiStack(API Gateway+Lambda, 最小権限)・WorkerStack(抽出ワーカー Lambda, SQSソース)・FrontendStack(S3+CloudFront, SPA)。`cdk synth` で CloudFormation 生成を検証（AWS 認証不要・未デプロイ）。アプリ実体の bundling は段階的（本 intent はインフラ骨子）。

## Slug
noshi-cdk-infra

## Type
feature（IaC・技術ハードニング）

## Upstream
- org-ai-kb/design-reviews/ux-product-review-002.md（N4）
- intent-002 infrastructure-design.md / deployment-architecture.md
