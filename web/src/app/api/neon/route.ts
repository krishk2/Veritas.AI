import { NextResponse } from "next/server";
import { sql, s3, BUCKET_NAME, uploadMediaToNeon } from "@/lib/neon";
import { ListObjectsV2Command } from "@aws-sdk/client-s3";

export async function GET() {
  const telemetry = {
    postgres: { status: "unknown", latency_ms: 0, details: {} },
    object_storage: { status: "unknown", latency_ms: 0, details: {} },
    timestamp: new Date().toISOString(),
  };

  // 1. Test Neon Serverless Postgres
  const pgStart = Date.now();
  try {
    const rows = await sql`
      SELECT 
        NOW() as server_time,
        current_database() as database,
        (SELECT count(*) FROM claim_records) as total_claims;
    `;
    telemetry.postgres = {
      status: "connected",
      latency_ms: Date.now() - pgStart,
      details: rows[0] || {},
    };
  } catch (err: any) {
    telemetry.postgres = {
      status: "error",
      latency_ms: Date.now() - pgStart,
      details: { error: err.message },
    };
  }

  // 2. Test Neon Object Storage (Bucket listing & connectivity)
  const s3Start = Date.now();
  try {
    const listRes = await s3.send(
      new ListObjectsV2Command({
        Bucket: BUCKET_NAME,
        MaxKeys: 5,
      })
    );
    telemetry.object_storage = {
      status: "connected",
      latency_ms: Date.now() - s3Start,
      details: {
        bucket: BUCKET_NAME,
        objects_count: listRes.KeyCount || 0,
        region: process.env.AWS_REGION || "eu-central-1",
      },
    };
  } catch (err: any) {
    telemetry.object_storage = {
      status: "error",
      latency_ms: Date.now() - s3Start,
      details: { error: err.message },
    };
  }

  return NextResponse.json(telemetry);
}

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    const uploadRes = await uploadMediaToNeon(buffer, file.name, file.type);
    return NextResponse.json({ success: true, ...uploadRes });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
