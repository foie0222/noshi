import { Stack, StackProps, CfnOutput } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as iam from "aws-cdk-lib/aws-iam";

interface GithubOidcStackProps extends StackProps {
  /** "owner/repo" 形式（例: foie0222/noshi）。 */
  githubRepo: string;
  /** デプロイを許可するブランチ（既定 main）。 */
  branch?: string;
}

/**
 * GithubOidcStack — GitHub Actions から OIDC で AWS にデプロイするための
 * Identity Provider と IAM ロール。長期アクセスキーを使わない。
 *
 * ロールは指定リポジトリの指定ブランチ(main)の push にのみ信頼され、
 * CDK ブートストラップロール(cdk-*)を assume して `cdk deploy` を実行する。
 * このスタックは（自己参照のため）デプロイワークフローには含めず、初回に手動 deploy する。
 */
export class GithubOidcStack extends Stack {
  constructor(scope: Construct, id: string, props: GithubOidcStackProps) {
    super(scope, id, props);
    const branch = props.branch ?? "main";

    const provider = new iam.OpenIdConnectProvider(this, "GithubOidcProvider", {
      url: "https://token.actions.githubusercontent.com",
      clientIds: ["sts.amazonaws.com"],
    });

    const role = new iam.Role(this, "GithubDeployRole", {
      roleName: "noshi-github-deploy",
      description: "GitHub Actions (OIDC) deploy role for noshi",
      maxSessionDuration: undefined,
      assumedBy: new iam.WebIdentityPrincipal(provider.openIdConnectProviderArn, {
        StringEquals: {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        },
        StringLike: {
          // 指定リポジトリ・指定ブランチの push にのみ許可
          "token.actions.githubusercontent.com:sub": `repo:${props.githubRepo}:ref:refs/heads/${branch}`,
        },
      }),
    });

    // CDK ブートストラップロール(deploy/file-publishing/lookup 等)を assume して cdk deploy する
    role.addToPolicy(
      new iam.PolicyStatement({
        actions: ["sts:AssumeRole", "sts:TagSession"],
        resources: [`arn:aws:iam::${this.account}:role/cdk-*`],
      }),
    );

    new CfnOutput(this, "DeployRoleArn", { value: role.roleArn });
    new CfnOutput(this, "DeployRoleName", { value: role.roleName });
  }
}
