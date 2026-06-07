#!/usr/bin/env node
import { App } from "aws-cdk-lib";
import { DataStack } from "../lib/data-stack";
import { MessagingStack } from "../lib/messaging-stack";
import { AuthStack } from "../lib/auth-stack";
import { ApiStack } from "../lib/api-stack";
import { WorkerStack } from "../lib/worker-stack";
import { FrontendStack } from "../lib/frontend-stack";

// noshi インフラ（infrastructure-design.md / deployment-architecture.md）。リージョン ap-northeast-1。
const app = new App();
const env = { region: "ap-northeast-1" };

const data = new DataStack(app, "NoshiDataStack", { env });
const messaging = new MessagingStack(app, "NoshiMessagingStack", { env });
const auth = new AuthStack(app, "NoshiAuthStack", { env });
new ApiStack(app, "NoshiApiStack", { env, table: data.table, queue: messaging.extractionQueue, imageBucket: data.imageBucket, userPoolId: auth.userPool.userPoolId });
new WorkerStack(app, "NoshiWorkerStack", { env, table: data.table, queue: messaging.extractionQueue });
new FrontendStack(app, "NoshiFrontendStack", { env });
