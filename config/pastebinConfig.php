<?php
// ====== Basic Settings ======
// Optional theme color : amber blue blue-grey brown cyan deep-orange deep-purple green grey indigo light-blue light-green lime orange pink purple red teal yellow
define('SITE_NAME', 'FIFCOM Pastebin');
define('PRIMARY_THEME', 'indigo');
define('ACCENT_THEME', 'pink');
define('ICON_URL', 'https://q.qlogo.cn/headimg_dl?dst_uin=1280874899&spec=640');
define('TITLE_MAX_LENTH', '100'); // defalt 0.1kb
define('PASTEBIN_MAX_LENTH', '102400'); // defalt 100kb (1024 * 100)
//define('ADMIN_ACCESS_KEY', '1145141919810');

// ====== Advanced Settings =======
define('TLS_ENCRYPT', 'disable'); // enable or disable, recommended to enable.
define('PASTEBIN_CRYPT_IV', 'pastebin11451419'); // precisely 16 bytes long.
define('PASTEBIN_SECURITY_TOKEN', 'pastebin114514'); // any string.

// ====== Others ======
define('PASTEBIN_VERSION', 'v2.0 (Beta 2103)'); // DON'T change.
define('SITE_URL', ''); // custom site url, '' = defalt

error_reporting(E_ALL);
$_ERROR = array();