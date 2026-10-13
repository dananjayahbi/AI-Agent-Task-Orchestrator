/**
 * Attachment content queries (MT-4.6-04; Section 9.5 retrieval table;
 * Section 9.2 `GET /attachments/{id}/content?format=&page=`).
 *
 * One cache entry per attachment × format × page — pages are fetched
 * only when the viewer addresses them (RISK-13: one page per request,
 * never a whole-document preload). Everything flows through the
 * generated client's credentialed fetch, which is also the auth-aware
 * path for images: the normalized bytes come back as `image_base64`
 * inside the JSON envelope and render as a `data:` URL — the browser
 * never makes a second, cookie-less request for image markup.
 *
 * `ATTACHMENT_NOT_READY` (409) and `ATTACHMENT_UNSUPPORTED_FORMAT`
 * (415) surface as catalog-mapped `ApiError`s; the viewer maps them to
 * friendly states (Section 20.4 item 5) — this module never invents
 * handling for codes outside the catalog.
 */
import { useQuery } from '@tanstack/react-query';

import { callApi, retrieveAttachmentContent } from '@/lib/api';
import type { AttachmentContent } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

/** Section 9.5 concrete formats (`auto` never reaches the wire). */
export type AttachmentContentFormat = 'image_base64' | 'text_ocr' | 'markdown';

/** Fetch one addressed content page through the generated client. */
export function fetchAttachmentContent(
  attachmentId: string,
  format: AttachmentContentFormat,
  page: number | null,
): Promise<AttachmentContent> {
  return callApi(
    retrieveAttachmentContent({
      path: { id: attachmentId },
      query: {
        format,
        ...(page !== null ? { page } : {}),
      },
    }),
  );
}

/**
 * One addressed content page. Disabled while the attachment id is null
 * (nothing selected) — the cache key carries format and page so tab
 * switches and page navigation each land on their own entry.
 */
export function useAttachmentContentQuery(
  attachmentId: string | null,
  format: AttachmentContentFormat,
  page: number | null,
) {
  return useQuery({
    queryKey: queryKeys.attachmentContent(attachmentId ?? 'none', format, page),
    queryFn: () => fetchAttachmentContent(attachmentId ?? '', format, page),
    enabled: attachmentId !== null,
    staleTime: 60_000,
    retry: false,
  });
}
