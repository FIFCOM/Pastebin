import { apiHttp } from './http'

export interface InstallEnvItem {
  key: string
  default_value: string
  comment: string | null
  required: boolean
  advanced: boolean
  group: string | null
}

export interface InstallContextResponse {
  needs_install: boolean
  env_exists: boolean
  admin_exists: boolean
  env_template: InstallEnvItem[]
  restart_required: boolean
  restart_message: string | null
}

export interface InstallSetupRequest {
  env_values: Record<string, string>
  admin_email?: string
  admin_password?: string
}

export interface InstallSetupResponse {
  message: string
  env_created: boolean
  admin_created: boolean
  restart_required: boolean
}

let inFlight: Promise<InstallContextResponse> | null = null

export async function fetchInstallContext(
  options: { force?: boolean } = {}
): Promise<InstallContextResponse> {
  if (!options.force && inFlight) return inFlight

  const requestPromise = apiHttp
    .get<InstallContextResponse>('/install/context')
    .then((resp) => resp.data)
    .finally(() => {
      if (inFlight === requestPromise) {
        inFlight = null
      }
    })

  inFlight = requestPromise
  return requestPromise
}

export async function runInstallSetup(payload: InstallSetupRequest): Promise<InstallSetupResponse> {
  const response = await apiHttp.post<InstallSetupResponse>('/install/setup', payload)
  return response.data
}
