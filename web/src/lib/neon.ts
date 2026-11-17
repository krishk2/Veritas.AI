import { neon } from "@neondatabase/serverless";
import {
  S3Client,
  PutObjectCommand,
  ListObjectsV2Command,
  GetObjectCommand,
} from "@aws-sdk/client-s3";

// 1. Neon Serverless Postgres Client
// Uses connection pooling via process.env.DATABASE_URL
const databaseUrl =
  process.env.DATABASE_URL ||
  "postgresql://neondb_owner:npg_qonfMQd6GbO4@ep-silent-silence-b9lhh1ij-pooler.c-7.eu-central-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require";

export const sql = neon(databaseUrl);

// 2. Neon Object Storage S3 Client (Assets Bucket)
export const BUCKET_NAME = "assets";

export const s3 = new S3Client({
  region: process.env.AWS_REGION || "eu-central-1",
  endpoint:
    process.env.AWS_ENDPOINT_URL_S3 ||
    "https://br-twilight-poetry-b9w6xu1x.storage.c-7.eu-central-1.aws.neon.tech",
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID || "",
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || "",
  },
  forcePathStyle: true,
});

/**
 * Uploads media assets (images/videos) to Neon Object Storage
 */
export async function uploadMediaToNeon(
  fileBuffer: Buffer,
  fileName: string,
  contentType: string
): Promise<{ key: string; url: string }> {
  const key = `uploads/${Date.now()}-${fileName}`;

  await s3.send(
    new PutObjectCommand({
      Bucket: BUCKET_NAME,
      Key: key,
      Body: fileBuffer,
      ContentType: contentType,
    })
  );

  const endpoint = process.env.AWS_ENDPOINT_URL_S3 || "";
  const url = `${endpoint}/${BUCKET_NAME}/${key}`;

  return { key, url };
}
