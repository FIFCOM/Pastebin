import { createInstallAwareHttpClient } from './http'

const apiClient = createInstallAwareHttpClient()

export async function getApiDocsMarkdown(slug: string): Promise<string> {
  const path = slug === 'overview' ? '/docs' : `/docs/${encodeURIComponent(slug)}`
  const response = await apiClient.get<string>(path, {
    responseType: 'text'
  })
  return response.data
}
