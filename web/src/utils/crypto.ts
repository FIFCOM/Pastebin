/**
 * 加密工具模块 - AES-GCM
 *
 * 约定：encrypted_data = IV(12B) + ciphertext_and_tag
 * - IV: 96-bit (12 bytes)
 * - Key: 16 bytes (AES-128) 或 32 bytes (AES-256)，需与后端 ENCRYPTION_KEY_LENGTH 一致
 */

const AES_GCM_IV_LENGTH = 12
const AES_GCM_TAG_LENGTH = 16
const DEFAULT_KEY_LENGTH_BYTES = 16
const FILE_CHUNK_IV_PREFIX_LENGTH = 8
const AES_GCM_OVERHEAD_BYTES = AES_GCM_IV_LENGTH + AES_GCM_TAG_LENGTH
const FILE_CHUNK_AAD_PREFIX = 'mb:filechunk:v1'

type WebCryptoBytes = Uint8Array<ArrayBuffer>

function randomBytes(length: number): WebCryptoBytes {
  const bytes: WebCryptoBytes = new Uint8Array(length)
  crypto.getRandomValues(bytes)
  return bytes
}

function toWebCryptoBytes(bytes: Uint8Array): WebCryptoBytes {
  if (bytes.buffer instanceof ArrayBuffer) {
    return bytes as WebCryptoBytes
  }
  return new Uint8Array(bytes)
}

/**
 * 生成随机加密密钥
 * 对应后端: generate_encryption_key()
 */
export async function generateEncryptionKey(length: number = DEFAULT_KEY_LENGTH_BYTES): Promise<Uint8Array> {
  if (![16, 24, 32].includes(length)) {
    throw new Error(`无效的密钥长度: ${length}（必须为 16/24/32 字节）`)
  }

  return randomBytes(length)
}

function assertAesGcmKeyLength(key: Uint8Array): void {
  if (![16, 24, 32].includes(key.byteLength)) {
    throw new Error(`AES-GCM 密钥长度错误: ${key.byteLength}（必须为 16/24/32 字节）`)
  }
}

/**
 * 将字节数组转换为base64字符串
 * 对应后端: bytes_to_str()
 */
export function bytesToStr(data: Uint8Array): string {
  // 首选 TextDecoder('latin1')：避免 String.fromCharCode(...data) 在大数据上栈溢出
  try {
    const binary = new TextDecoder('latin1' as any).decode(data)
    return btoa(binary)
  } catch {
    const chunkSize = 0x8000
    let binary = ''
    for (let i = 0; i < data.length; i += chunkSize) {
      const chunk = data.subarray(i, i + chunkSize)
      binary += String.fromCharCode(...chunk)
    }
    return btoa(binary)
  }
}

/**
 * 将base64字符串转换为字节数组
 * 对应后端: str_to_bytes()
 */
export function strToBytes(data: string): Uint8Array {
  let binaryString: string
  try {
    binaryString = atob(data)
  } catch (e: any) {
    throw new Error(`Base64 解码失败: ${e?.message || String(e)}`)
  }

  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) bytes[i] = binaryString.charCodeAt(i)
  return bytes
}

/**
 * 将加密密钥转换为URL-safe base64字符串
 * 专门用于加密密钥的编码，使其可以安全地用于URL
 */
export function keyToUrlSafeStr(key: Uint8Array): string {
  const base64 = bytesToStr(key)
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

/**
 * 将URL-safe base64字符串转换为加密密钥
 * 专门用于加密密钥的解码
 */
export function urlSafeStrToKey(
  urlSafeBase64: string,
  expectedKeyLengths: number[] = [16, 24, 32]
): Uint8Array {
  if (!urlSafeBase64 || urlSafeBase64.trim() === '') {
    throw new Error('加密密钥为空')
  }

  // 将URL-safe base64转换回标准base64
  let base64 = urlSafeBase64.replace(/-/g, '+').replace(/_/g, '/')
  // 补充padding
  while (base64.length % 4) {
    base64 += '='
  }

  const bytes = strToBytes(base64)
  if (!expectedKeyLengths.includes(bytes.byteLength)) {
    throw new Error(
      `加密密钥长度不合法: ${bytes.byteLength}（期望: ${expectedKeyLengths.join('/') } 字节）`
    )
  }
  return bytes
}

/**
 * 使用AES-GCM加密数据
 * 对应后端: encrypt_with_key()
 * 
 * @param data 要加密的数据（字节数组或字符串）
 * @param key 加密密钥（16/24/32字节）
 * @param options.aad 可选A(A)D上下文绑定
 * @param options.iv 可选外部指定IV（必须12字节；分片/确定性nonce场景）
 * @returns 加密后的数据（包含IV和密文）
 */
export async function encryptWithKey(
  data: Uint8Array | string,
  key: Uint8Array,
  options?: { aad?: Uint8Array; iv?: Uint8Array }
): Promise<Uint8Array> {
  assertAesGcmKeyLength(key)

  // 如果是字符串，转换为字节数组
  const dataBytes =
    typeof data === 'string' ? new TextEncoder().encode(data) : toWebCryptoBytes(data)
  const keyBytes = toWebCryptoBytes(key)

  // 生成随机IV (12字节用于GCM) 或使用外部IV
  const iv = options?.iv ? toWebCryptoBytes(options.iv) : randomBytes(AES_GCM_IV_LENGTH)
  if (iv.byteLength !== AES_GCM_IV_LENGTH) {
    throw new Error(`IV长度错误: ${iv.byteLength}（必须为 ${AES_GCM_IV_LENGTH} 字节）`)
  }

  // 导入密钥
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'AES-GCM' },
    false,
    ['encrypt']
  )

  const algorithm: AesGcmParams = {
    name: 'AES-GCM',
    iv
  }
  if (options?.aad) {
    algorithm.additionalData = toWebCryptoBytes(options.aad)
  }

  // 加密数据
  const encrypted = await crypto.subtle.encrypt(
    algorithm,
    cryptoKey,
    dataBytes
  )

  // 组合 IV + 密文
  const result = new Uint8Array(iv.length + encrypted.byteLength)
  result.set(iv, 0)
  result.set(new Uint8Array(encrypted), iv.length)

  return result
}

/**
 * 使用AES-GCM解密数据
 * 对应后端: decrypt_with_key()
 * 
 * @param encryptedData 加密的数据（包含IV和密文）
 * @param key 解密密钥（16/24/32字节）
 * @param options.aad 可选A(A)D上下文绑定（必须与加密时一致）
 * @returns 解密后的数据
 */
export async function decryptWithKey(
  encryptedData: Uint8Array,
  key: Uint8Array,
  options?: { aad?: Uint8Array }
): Promise<Uint8Array> {
  assertAesGcmKeyLength(key)
  if (encryptedData.byteLength < AES_GCM_IV_LENGTH + AES_GCM_TAG_LENGTH) {
    throw new Error(`加密数据长度不足: ${encryptedData.byteLength}`)
  }

  // 提取IV和密文
  const iv = toWebCryptoBytes(encryptedData.slice(0, AES_GCM_IV_LENGTH))
  const ciphertext = toWebCryptoBytes(encryptedData.slice(AES_GCM_IV_LENGTH))
  const keyBytes = toWebCryptoBytes(key)

  // 导入密钥
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'AES-GCM' },
    false,
    ['decrypt']
  )

  const algorithm: AesGcmParams = {
    name: 'AES-GCM',
    iv
  }
  if (options?.aad) {
    algorithm.additionalData = toWebCryptoBytes(options.aad)
  }

  // 解密数据
  const decrypted = await crypto.subtle.decrypt(
    algorithm,
    cryptoKey,
    ciphertext
  )

  return new Uint8Array(decrypted)
}

/**
 * 加密字符串内容并返回base64编码
 * 
 * @param content 要加密的字符串内容
 * @param key 加密密钥（16/24/32字节）
 * @returns base64编码的加密数据
 */
export async function encryptContent(content: string, key: Uint8Array): Promise<string> {
  const encrypted = await encryptWithKey(content, key)
  return bytesToStr(encrypted)
}

/**
 * 解密base64编码的加密内容
 * 
 * @param encryptedContent base64编码的加密数据
 * @param key 解密密钥（16/24/32字节）
 * @returns 解密后的字符串
 */
export async function decryptContent(
  encryptedContent: string,
  key: Uint8Array
): Promise<string> {
  const encryptedBytes = strToBytes(encryptedContent)
  const decrypted = await decryptWithKey(encryptedBytes, key)
  return new TextDecoder().decode(decrypted)
}

/**
 * 构造分片上传的 AAD（需与后端一致）
 */
export function buildFileChunkAad(
  pasteId: string,
  fileId: string,
  chunkIndex: number,
  totalChunks: number
): Uint8Array {
  const aadStr = `${FILE_CHUNK_AAD_PREFIX}|paste:${pasteId}|file:${fileId}|i:${chunkIndex}|n:${totalChunks}`
  return new TextEncoder().encode(aadStr)
}

/**
 * 构造 deterministic nonce: prefix8 + chunk_index(4B大端)
 *
 * 分片上传请使用 `deriveIvPrefix8FromUploadId(uploadId)` 生成 prefix8，避免同 key 下 IV 重用。
 */
export function buildFileChunkIv(prefix8: Uint8Array, chunkIndex: number): Uint8Array {
  if (prefix8.byteLength !== FILE_CHUNK_IV_PREFIX_LENGTH) {
    throw new Error(`IV前缀长度错误: ${prefix8.byteLength}（必须为8字节）`)
  }
  if (!Number.isInteger(chunkIndex) || chunkIndex < 0 || chunkIndex > 0xffffffff) {
    throw new Error(`chunkIndex无效: ${chunkIndex}`)
  }

  const iv = new Uint8Array(AES_GCM_IV_LENGTH)
  iv.set(prefix8, 0)
  iv[8] = (chunkIndex >>> 24) & 0xff
  iv[9] = (chunkIndex >>> 16) & 0xff
  iv[10] = (chunkIndex >>> 8) & 0xff
  iv[11] = chunkIndex & 0xff
  return iv
}

/**
 * 从 upload_id 派生 IV 前缀（与后端一致）：prefix8 = SHA-256(utf8(upload_id))[0..8)
 *
 * 用途：分片上传（client/server）统一使用 deterministic nonce: prefix8 + chunkIndex(4B大端)。
 * 这样即使用户重复上传同一文件（upload_id 不同），也不会在同一 key 下发生 IV 重用。
 */
export async function deriveIvPrefix8FromUploadId(uploadId: string): Promise<Uint8Array> {
  if (!uploadId || uploadId.trim() === '') {
    throw new Error('uploadId为空')
  }
  const bytes = new TextEncoder().encode(uploadId)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return new Uint8Array(digest).slice(0, FILE_CHUNK_IV_PREFIX_LENGTH)
}

export function getAesGcmEncryptedLength(plaintextLength: number): number {
  if (!Number.isFinite(plaintextLength) || plaintextLength < 0) {
    throw new Error(`plaintextLength无效: ${plaintextLength}`)
  }
  return plaintextLength + AES_GCM_OVERHEAD_BYTES
}

/**
 * 分片加密高层封装（client 分片上传使用）
 *
 * 约束：
 * - IV: deterministic = SHA-256(upload_id)[:8] + chunkIndex(4B大端)
 * - AAD: FILE_CHUNK_AAD_PREFIX + paste/file/index/total
 * - 输出长度必须等于 明文长度 + 28
 *
 * 注意：fileId 必须为 upload_id（与后端一致）；这里显式保留参数以避免调用方混淆。
 */
export async function encryptFileChunk(
  chunkPlaintext: Uint8Array,
  key: Uint8Array,
  params: {
    pasteId: string
    uploadId: string
    fileId: string
    chunkIndex: number
    totalChunks: number
  }
): Promise<Uint8Array> {
  if (params.fileId !== params.uploadId) {
    throw new Error('fileId必须等于uploadId（即init返回的upload_id）')
  }
  if (chunkPlaintext.byteLength < 0) {
    throw new Error('chunkPlaintext无效')
  }
  if (!Number.isInteger(params.chunkIndex) || params.chunkIndex < 0) {
    throw new Error(`chunkIndex无效: ${params.chunkIndex}`)
  }
  if (!Number.isInteger(params.totalChunks) || params.totalChunks <= 0) {
    throw new Error(`totalChunks无效: ${params.totalChunks}`)
  }
  if (params.chunkIndex >= params.totalChunks) {
    throw new Error('chunkIndex越界')
  }

  const prefix8 = await deriveIvPrefix8FromUploadId(params.uploadId)
  const iv = buildFileChunkIv(prefix8, params.chunkIndex)
  const aad = buildFileChunkAad(
    params.pasteId,
    params.fileId,
    params.chunkIndex,
    params.totalChunks
  )

  const encrypted = await encryptWithKey(chunkPlaintext, key, { iv, aad })
  const expectedLen = getAesGcmEncryptedLength(chunkPlaintext.byteLength)
  if (encrypted.byteLength !== expectedLen) {
    throw new Error(`加密分片长度不匹配: expected=${expectedLen}, got=${encrypted.byteLength}`)
  }
  return encrypted
}
