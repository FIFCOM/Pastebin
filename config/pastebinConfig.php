<?php
// ====== Basic Settings ======
// Optional theme color : amber blue blue-grey brown cyan deep-orange deep-purple green grey indigo light-blue light-green lime orange pink purple red teal yellow
const SITE_NAME = 'FIFCOM Pastebin';
const PRIMARY_THEME = 'teal';
const ACCENT_THEME = 'indigo';
const ICON_URL = 'https://q.qlogo.cn/headimg_dl?dst_uin=1280874899&spec=640';
const TITLE_MAX_LENGTH = '100'; // default 0.1kb
const PASTEBIN_MAX_LENGTH = '100'; // default 100kb
const FILE_MAX_LENGTH = '100'; // default 100kb

// ====== Advanced Settings =======
const TLS_ENCRYPT = 'disable'; // enable or disable, recommended to enable.
const PASTEBIN_CRYPT_IV = 'pastebin11451419'; // precisely 16 bytes long.

// ====== Others ======
const PASTEBIN_VERSION = 'v2.0 (Beta 2103)'; // DON'T change.
const SITE_URL = ''; // custom site url, '' = default

error_reporting(E_ALL);
$_ERROR = array();