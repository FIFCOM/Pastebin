<?php
// ====== Basic Settings ======
// Optional theme color :
// amber blue blue-grey brown cyan deep-orange deep-purple green grey indigo
// light-blue light-green lime orange pink purple red teal yellow

const SITE_NAME = 'FIFCOM Pastebin';
const PRIMARY_THEME = 'teal';
const ACCENT_THEME = 'indigo';
const ICON_URL = 'https://q.qlogo.cn/headimg_dl?dst_uin=1280874899&spec=640';
const TITLE_MAX_LENGTH = '100'; // default 100 byte
const PASTEBIN_MAX_LENGTH = '100'; // default 100kb
const FILE_MAX_SIZE = '10240'; // default 10240kb == 10mb
const PASTEBIN_DB_HOSTNAME = 'localhost';
const PASTEBIN_DB_USERNAME = 'root';
const PASTEBIN_DB_PASSWORD = 'localhost';
const PASTEBIN_DB_NAME = 'pastebin';

// ====== Advanced Settings =======
const TLS_ENCRYPT = 'disable'; // enable or disable.
const PASTEBIN_SECURITY_TOKEN = 'pastebin11451419'; // any string , strlen(PASTEBIN_CRYPT_IV) == 16

// ====== Others ======
const PASTEBIN_VERSION = 'v2.0 (Beta 2105)';
const SITE_URL = ''; // custom site url, '' = auto

error_reporting(E_ALL);
$_ERROR = array();