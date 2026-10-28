# External Platform Integration Setup

This document describes the external API connectors included in the research implementation. A platform is **configured** only when its required environment variables are present. That check does not verify token validity, app approval, permissions, account eligibility, billing, or successful publishing.

## Environment configuration

Copy the relevant entries from `.env.example` into the local `.env` file or deployment secret store. Never commit real tokens.

- `META_GRAPH_API_VERSION`: a Graph API version currently supported by the connected Meta app.
- `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp Business Platform Cloud API credentials.
- `FACEBOOK_PAGE_ID` and `FACEBOOK_PAGE_ACCESS_TOKEN`: Facebook Page credentials with permission to publish Page posts.
- `INSTAGRAM_BUSINESS_ACCOUNT_ID` and `META_GRAPH_ACCESS_TOKEN`: Instagram professional-account publishing credentials and the required publishing permission.
- `TIKTOK_ACCESS_TOKEN` and `TIKTOK_OPEN_ID`: TikTok user authorization and Content Posting API access.
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Google Gen AI access for text agents and the image-generation endpoint. Image model access and billing must also be enabled.

## API endpoints

All outbound actions below require an administrator JWT and an explicit `approved: true` field in the request body.

| Endpoint | Purpose | Important constraint |
|---|---|---|
| `GET /api/v1/platforms/status` | Show credential configuration state | Does not test credentials against providers |
| `POST /api/v1/platforms/whatsapp/messages` | Send a WhatsApp text message | Recipient must be eligible under WhatsApp messaging rules |
| `POST /api/v1/platforms/facebook/publish` | Publish a text post to a Facebook Page | Requires a valid Page token and publishing permissions |
| `POST /api/v1/platforms/instagram/publish-image` | Publish an image and caption | Image URL must be publicly accessible and satisfy Instagram requirements |
| `POST /api/v1/platforms/tiktok/publish-video` | Submit a video URL for TikTok publishing | Requires the approved Content Posting API scope and a verified media URL domain |
| `POST /api/v1/ai/agents/image-studio/render` | Generate a product image preview | Returns base64 image data; no permanent media hosting is configured |

## Request examples

WhatsApp:

```json
{
  "approved": true,
  "to": "+256700000000",
  "message": "Your order update is ready."
}
```

Facebook Page:

```json
{
  "approved": true,
  "message": "New products are available. Contact the store for current stock and prices."
}
```

Instagram:

```json
{
  "approved": true,
  "image_url": "https://your-verified-domain.example/product.jpg",
  "caption": "View the product details and contact the store for current availability."
}
```

TikTok:

```json
{
  "approved": true,
  "video_url": "https://your-verified-domain.example/product-video.mp4",
  "caption": "Product overview",
  "privacy_level": "SELF_ONLY"
}
```

The TikTok endpoint queries the creator's available privacy options before submitting the video. A returned publishing ID means the request was submitted for processing, not that the post is already public. TikTok notes that unaudited clients can be restricted to private posts.

## Research and operational limitations

1. Tokens must be created and authorized through the respective platform developer accounts. This repository cannot create platform approval or account permissions on the user's behalf.
2. Use test accounts and private visibility first. Do not automate bulk messages or advertising without reviewing consent, opt-in, platform policy, and applicable law.
3. Human review remains required before public-facing content is sent. The approval flag is a deliberate server-side gate; do not expose these admin routes to customers.
4. AI image output is a preview. Verify the depiction against the real product before publishing. The current endpoint returns image bytes as base64 and does not persist them or provide a public media URL.
5. The payment endpoint remains unconfigured. Select a payment provider and complete its signed callback/webhook verification before treating an order as paid.
6. Campaign scheduling, analytics ingestion, and a persistent publishing queue are not yet implemented. The current social connectors perform explicit, administrator-triggered actions rather than unattended scheduling.
