import crypto from 'crypto';
// @ts-ignore
import { AKSKSigner } from '@huaweicloud/huaweicloud-sdk-core/auth/AKSKSigner.js';

export interface SignOptions {
    method: string;
    url: string;
    headers: Record<string, string>;
    body?: string;
    service?: string;
}

export class HuaweiSigner {
    static sign(ak: string, sk: string, options: SignOptions): Record<string, string> {
        const { method, url, headers, body = '', service } = options;
        const parsedUrl = new URL(url);
        
        const isObs = service === 'obs' || parsedUrl.host.includes('obs.');
        
        if (isObs) {
            // Specialized OBS logic (S3-compatible)
            const now = new Date();
            const rfcDate = now.toUTCString();
            let canonicalResource = parsedUrl.pathname === '' ? '/' : parsedUrl.pathname;
            const hostParts = parsedUrl.host.split('.obs.');
            if (hostParts.length > 1) {
                const bucketName = hostParts[0];
                canonicalResource = `/${bucketName}${canonicalResource}`;
            }
            
            const contentType = headers['Content-Type'] || '';
            const stringToSign = `${method.toUpperCase()}\n\n${contentType}\n${rfcDate}\n${canonicalResource}`;
            const signature = crypto.createHmac('sha1', sk).update(stringToSign).digest('base64');
            
            return {
                ...headers,
                'Host': parsedUrl.host,
                'Date': rfcDate,
                'Authorization': `OBS ${ak}:${signature}`
            };
        }

        // Use the PURE official AKSKSigner for all other services
        const sdkRequest = {
            method: method.toUpperCase(),
            endpoint: url,
            headers: { ...headers },
            data: body ? JSON.parse(body) : undefined,
            queryParams: Object.fromEntries(parsedUrl.searchParams.entries())
        };

        const credential: any = {
            getAk: () => ak,
            getSk: () => sk
        };

        return AKSKSigner.sign(sdkRequest, credential);
    }
}
