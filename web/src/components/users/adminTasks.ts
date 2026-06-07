import type { CleanupTaskName } from '../../services/admin'

export const CLEANUP_TASK_ORDER: CleanupTaskName[] = [
  'expired_drafts',
  'expired_pastes',
  'expired_uploads',
  'expired_members',
  'expired_user_sessions',
  'expired_used_refresh_tokens'
]

export const CLEANUP_TASK_META: Record<CleanupTaskName, { label: string; description: string; icon: string }> = {
  expired_drafts: {
    label: '过期草稿',
    description: '清理超过草稿有效期且未发布的 Paste。',
    icon: 'edit_note'
  },
  expired_pastes: {
    label: '过期 Paste',
    description: '清理已发布但超过过期时间的 Paste。',
    icon: 'content_paste'
  },
  expired_uploads: {
    label: '过期上传',
    description: '清理未完成的分片上传会话和临时文件。',
    icon: 'upload_file'
  },
  expired_members: {
    label: '过期协作成员',
    description: '清理协作房间中过期的临时成员。',
    icon: 'groups'
  },
  expired_user_sessions: {
    label: '过期会话',
    description: '清理已过期的用户会话记录。',
    icon: 'devices'
  },
  expired_used_refresh_tokens: {
    label: '过期 Refresh Token 记录',
    description: '清理超过刷新令牌有效期的复用检测记录。',
    icon: 'vpn_key'
  }
}

export function sortedCleanupTasks(tasks: CleanupTaskName[]): CleanupTaskName[] {
  const order = new Map(CLEANUP_TASK_ORDER.map((task, index) => [task, index]))
  return [...tasks].sort((a, b) => (order.get(a) ?? 999) - (order.get(b) ?? 999))
}
