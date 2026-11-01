# 0004 — S3 API everywhere, RustFS for local development

**Context.** Avatars, signed contracts, generated PDFs and knowledge-base documents need
object storage. MinIO, the usual local S3 stand-in, discontinued its community edition
(no more Docker images on Docker Hub; repository archived in 2026).

**Decision.** Code talks only to the S3 API through the `ObjectStorage` port (boto3 under
the hood). Locally: RustFS (S3-compatible, single container). Production: AWS S3 or
Cloudflare R2, switched by `S3_ENDPOINT_URL` and credentials. Uploads use presigned URLs
so large files never pass through the API.

**Alternatives.** SeaweedFS, Garage, S3Proxy for local; local filesystem storage (no
parity with prod).

**Consequences.** Dev/prod parity on the API level; swapping the local implementation is a
Compose change only.
