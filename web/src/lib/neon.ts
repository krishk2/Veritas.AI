import { neon } from "@neondatabase/serverless";
import {
  S3Client,
  PutObjectCommand,
  ListObjectsV2Command,
  GetObjectCommand,
} from "@aws-sdk/client-s3";

// 1. Neon Serverless Postgres Client
// Supports standard DATABASE_URL as well as custom Vercel integration prefixes (e.g. storage_URL)
const databaseUrl =
  process.env.DATABASE_URL ||
  process.env.storage_URL_DATABASE_URL ||
  process.env.STORAGE_URL_DATABASE_URL ||
  process.env.storage_URL_POSTGRES_URL ||
  process.env.STORAGE_URL_POSTGRES_URL ||
  process.env.storage_URL_URL ||
  process.env.STORAGE_URL_URL ||
  (process.env.storage_URL?.startsWith("postgres") ? process.env.storage_URL : undefined) ||
  (process.env.STORAGE_URL?.startsWith("postgres") ? process.env.STORAGE_URL : undefined) ||
  process.env.POSTGRES_URL ||
  "postgresql://neondb_owner:npg_qonfMQd6GbO4@ep-silent-silence-b9lhh1ij-pooler.c-7.eu-central-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require";

export const sql = neon(databaseUrl);

// 2. Neon Object Storage S3 Client (Assets Bucket)
export const BUCKET_NAME = "assets";

const s3Endpoint =
  process.env.AWS_ENDPOINT_URL_S3 ||
  process.env.storage_URL_AWS_ENDPOINT_URL_S3 ||
  process.env.STORAGE_URL_AWS_ENDPOINT_URL_S3 ||
  process.env.storage_URL_ENDPOINT ||
  process.env.STORAGE_URL_ENDPOINT ||
  (process.env.storage_URL?.startsWith("http") && !process.env.storage_URL.includes("postgres") ? process.env.storage_URL : undefined) ||
  (process.env.STORAGE_URL?.startsWith("http") && !process.env.STORAGE_URL.includes("postgres") ? process.env.STORAGE_URL : undefined) ||
  "https://br-twilight-poetry-b9w6xu1x.storage.c-7.eu-central-1.aws.neon.tech";

const s3AccessKey =
  process.env.AWS_ACCESS_KEY_ID ||
  process.env.storage_URL_AWS_ACCESS_KEY_ID ||
  process.env.STORAGE_URL_AWS_ACCESS_KEY_ID ||
  process.env.storage_URL_ACCESS_KEY_ID ||
  process.env.STORAGE_URL_ACCESS_KEY_ID ||
  "";

const s3SecretKey =
  process.env.AWS_SECRET_ACCESS_KEY ||
  process.env.storage_URL_AWS_SECRET_ACCESS_KEY ||
  process.env.STORAGE_URL_AWS_SECRET_ACCESS_KEY ||
  process.env.storage_URL_SECRET_ACCESS_KEY ||
  process.env.STORAGE_URL_SECRET_ACCESS_KEY ||
  "";

const s3Region =
  process.env.AWS_REGION ||
  process.env.storage_URL_AWS_REGION ||
  process.env.STORAGE_URL_AWS_REGION ||
  "eu-central-1";

export const s3 = new S3Client({
  region: s3Region,
  endpoint: s3Endpoint,
  credentials: {
    accessKeyId: s3AccessKey,
    secretAccessKey: s3SecretKey,
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

  const endpoint = s3Endpoint || "";
  const url = `${endpoint}/${BUCKET_NAME}/${key}`;

  return { key, url };
}
