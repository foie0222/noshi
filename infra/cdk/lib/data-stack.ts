import { Stack, StackProps, RemovalPolicy, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as kms from "aws-cdk-lib/aws-kms";

/**
 * DataStack — ステートフル資源（infrastructure-design.md / deployment-architecture.md）。
 * DynamoDB（PK=USER#<userId> で本人スコープをキー設計に内包, PITR, TTL, GSI）/ S3（画像, SSE-KMS）/ KMS。
 * 削除保護つき（再デプロイでデータを保全）。
 */
export class DataStack extends Stack {
  public readonly table: dynamodb.Table;
  public readonly imageBucket: s3.Bucket;
  public readonly key: kms.Key;
  public readonly catalogTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    this.key = new kms.Key(this, "NoshiKey", {
      enableKeyRotation: true,
      description: "noshi data encryption key (at rest)",
    });

    // 単一テーブル: PK=USER#<userId>, SK=<TYPE>#<id>。GSI で status / party の検索。
    this.table = new dynamodb.Table(this, "NoshiTable", {
      tableName: "noshi",
      partitionKey: { name: "PK", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "SK", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST, // オンデマンド（NFR-S3）
      pointInTimeRecovery: true, // PITR（NFR-A2 RPO）
      timeToLiveAttribute: "ttl", // ExtractionJob.candidates の自動失効（NFR-D2）
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.key,
      removalPolicy: RemovalPolicy.RETAIN, // ステートフル: 削除保護
    });
    this.table.addGlobalSecondaryIndex({
      indexName: "gsi-status",
      partitionKey: { name: "GSI1PK", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "GSI1SK", type: dynamodb.AttributeType.STRING },
    });

    this.imageBucket = new s3.Bucket(this, "NoshiImages", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      // 署名付きPUT（ブラウザ直アップロード）を簡潔にするため SSE-S3。KMS だと
      // PUT 時に SSE 関連ヘッダの整合が必要になり、ブラウザからの直アップロードが煩雑。
      encryption: s3.BucketEncryption.S3_MANAGED,
      versioned: true, // RPO
      enforceSSL: true,
      // 署名付きでのブラウザ直アップロード/表示を許可（#35）。アクセス自体は署名で制限。
      cors: [
        {
          // POST: サイズ上限つき署名付き POST（#100）。GET/HEAD: 署名付き表示。
          allowedMethods: [s3.HttpMethods.POST, s3.HttpMethods.GET, s3.HttpMethods.HEAD],
          allowedOrigins: ["*"],
          allowedHeaders: ["*"],
          maxAge: 3000,
        },
      ],
      lifecycleRules: [{ abortIncompleteMultipartUploadAfter: Duration.days(1) }],
      removalPolicy: RemovalPolicy.RETAIN,
    });

    // カタログテーブル（お返し品提案）。中身は楽天の公開商品データで
    // 再構築可能なキャッシュ — ユーザーデータと分離し、CMK/PITR/RETAIN は適用しない。
    this.catalogTable = new dynamodb.Table(this, "NoshiCatalogTable", {
      tableName: "noshi-catalog",
      partitionKey: { name: "PK", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "SK", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "expiresAt", // 商品48h / クリック13ヶ月（書き込み側で設定）
      removalPolicy: RemovalPolicy.DESTROY, // 再構築可能なキャッシュ
    });
  }
}
