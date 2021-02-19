<?php
// ====== Basic Settings ======
// Optional theme color : amber blue blue-grey brown cyan deep-orange deep-purple green grey indigo light-blue light-green lime orange pink purple red teal yellow
const SITE_NAME = 'FIFCOM Pastebin [Beta]';
const PRIMARY_THEME = 'indigo';
const ACCENT_THEME = 'pink';
const ICON_URL = 'https://q.qlogo.cn/headimg_dl?dst_uin=1280874899&spec=640';
const TITLE_MAX_LENTH = '100'; // defalt 0.1kb
const PASTEBIN_MAX_LENTH = '102400'; // defalt 100kb (1024 * 100)

// ====== Advanced Settings =======
const TLS_ENCRYPT = 'disable'; // enable or disable, recommended to enable.
const PASTEBIN_CRYPT_IV = 'pastebin11451419'; // precisely 16 bytes long.
const PASTEBIN_SECURITY_TOKEN = 'pastebin114514'; // any string.

// ====== Others ======
const PASTEBIN_VERSION = 'v2.0 (Beta 2102)';

error_reporting(E_ALL);
$_ERROR = array();