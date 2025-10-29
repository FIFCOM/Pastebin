/**
 * 加密工具模块 - 与后端加密逻辑保持一致
 * 后端使用: Fernet (AES-128 CBC + HMAC SHA256)
 * 前端使用: Web Crypto API (AES-GCM 256位)
 */

/**
 * 生成随机加密密钥 (32字节 = 256位)
 * 对应后端: generate_encryption_key()
 */
export async function generateEncryptionKey(): Promise<Uint8Array> {
  const key = new Uint8Array(32) // 32字节 = 256位
  crypto.getRandomValues(key)
  return key
}

/**
 * 将字节数组转换为base64字符串
 * 对应后端: bytes_to_str()
 */
export function bytesToStr(data: Uint8Array): string {
  return btoa(String.fromCharCode(...data))
}

/**
 * 将base64字符串转换为字节数组
 * 对应后端: str_to_bytes()
 */
export function strToBytes(data: string): Uint8Array {
  const binaryString = atob(data)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }
  return bytes
}

/**
 * 使用AES-GCM加密数据
 * 对应后端: encrypt_with_key()
 * 
 * @param data 要加密的数据（字节数组或字符串）
 * @param key 加密密钥（32字节）
 * @returns 加密后的数据（包含IV和密文）
 */
export async function encryptWithKey(
  data: Uint8Array | string,
  key: Uint8Array
): Promise<Uint8Array> {
  // 如果是字符串，转换为字节数组
  const dataBytes = typeof data === 'string' ? new TextEncoder().encode(data) : data

  // 生成随机IV (12字节用于GCM)
  const iv = new Uint8Array(12)
  crypto.getRandomValues(iv)

  // 导入密钥
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    key.buffer as ArrayBuffer,
    { name: 'AES-GCM' },
    false,
    ['encrypt']
  )

  // 加密数据
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    cryptoKey,
    dataBytes.buffer as ArrayBuffer
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
 * @param key 解密密钥（32字节）
 * @returns 解密后的数据
 */
export async function decryptWithKey(
  encryptedData: Uint8Array,
  key: Uint8Array
): Promise<Uint8Array> {
  // 提取IV和密文
  const iv = encryptedData.slice(0, 12)
  const ciphertext = encryptedData.slice(12)

  // 导入密钥
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    key.buffer as ArrayBuffer,
    { name: 'AES-GCM' },
    false,
    ['decrypt']
  )

  // 解密数据
  const decrypted = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    cryptoKey,
    ciphertext
  )

  return new Uint8Array(decrypted)
}

/**
 * 加密字符串内容并返回base64编码
 * 
 * @param content 要加密的字符串内容
 * @param key 加密密钥（32字节）
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
 * @param key 解密密钥（32字节）
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