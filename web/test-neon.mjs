import { neon } from '@neondatabase/serverless';
import { S3Client, ListObjectsV2Command, PutObjectCommand } from '@aws-sdk/client-s3';

async function runTest() {
  console.log('=== Neon E2E Verification Test ===');
  
  // 1. Neon Serverless Postgres Test
  console.log('\n[1/2] Connecting to Neon Serverless Postgres via @neondatabase/serverless...');
  const sql = neon(process.env.DATABASE_URL);
  const t0 = Date.now();
  const dbResult = await sql`
    SELECT 
      NOW() as timestamp,
      current_database() as database,
      version() as pg_version,
      (SELECT COUNT(*) FROM claim_records) as total_claims
  `;
  const dbLatency = Date.now() - t0;
  console.log('✅ Neon Postgres Query Success!');
  console.log(`   Timestamp: ${dbResult[0].timestamp}`);
  console.log(`   Database: ${dbResult[0].database}`);
  console.log(`   Version: ${dbResult[0].pg_version.split(' ')[0]} ${dbResult[0].pg_version.split(' ')[1]}`);
  console.log(`   Claim Records in Neon DB: ${dbResult[0].total_claims}`);
  console.log(`   Round-trip Latency: ${dbLatency}ms`);

  // 2. Neon S3-Compatible Object Storage Test
  console.log('\n[2/2] Connecting to Neon Object Storage (Bucket: assets)...');
  const s3 = new S3Client({
    region: process.env.AWS_REGION || 'eu-central-1',
    endpoint: process.env.AWS_ENDPOINT_URL_S3,
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    },
    forcePathStyle: true,
  });

  // Test PutObject
  const testKey = `test-e2e-${Date.now()}.json`;
  const putStart = Date.now();
  await s3.send(new PutObjectCommand({
    Bucket: 'assets',
    Key: testKey,
    Body: JSON.stringify({ test: 'veritas-neon-e2e', created: new Date().toISOString() }),
    ContentType: 'application/json',
  }));
  const putLatency = Date.now() - putStart;
  console.log(`✅ Uploaded test object '${testKey}' in ${putLatency}ms`);

  // Test ListObjectsV2
  const listStart = Date.now();
  const listRes = await s3.send(new ListObjectsV2Command({
    Bucket: 'assets',
    MaxKeys: 10,
  }));
  const listLatency = Date.now() - listStart;
  console.log('✅ Neon Object Storage List Success!');
  console.log(`   Bucket: assets`);
  console.log(`   Key Count: ${listRes.KeyCount}`);
  console.log(`   Objects: ${listRes.Contents?.map(c => c.Key).join(', ')}`);
  console.log(`   List Latency: ${listLatency}ms`);

  console.log('\n=== ALL NEON SERVICES VERIFIED END-TO-END ===');
}

runTest().catch((err) => {
  console.error('❌ Neon verification failed:', err);
  process.exit(1);
});
