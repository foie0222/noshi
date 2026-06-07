# Business Logic Model — noshi CDK infra（intent-009）
## Unit scope
- Unit: noshi-service。Stories: S9-1/2。Owning: インフラ（CDK スタック群）。
## 構成
- Data/Messaging/Api/Worker/Frontend スタック（deployment-architecture 準拠）。依存: Api/Worker→Data/Messaging。
## 不変
- アプリのドメインは不変。インフラは intent-002 設計に準拠。
