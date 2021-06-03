<?php
// ====== Basic Settings ======
// Optional theme color :
// amber blue blue-grey brown cyan deep-orange deep-purple green grey indigo
// light-blue light-green lime orange pink purple red teal yellow

const SITE_NAME = 'FIFCOM Pastebin';
const PRIMARY_THEME = 'teal';
const ACCENT_THEME = 'indigo';
const ICON_URL = 'https://fifcom.cn/avatar/?transparent=1';
const TITLE_MAX_LENGTH = '100'; // default 100 byte
const PASTEBIN_MAX_LENGTH = '100'; // default 100kb
// const FILE_MAX_SIZE = '10240'; // deprecated
const PASTEBIN_DB_HOSTNAME = 'localhost';
const PASTEBIN_DB_USERNAME = 'root';
const PASTEBIN_DB_PASSWORD = 'localhost';
const PASTEBIN_DB_NAME = 'pastebin';

// ====== Advanced Settings =======
const TLS_ENCRYPT = 'auto'; // enable or disable or auto.
const PASTEBIN_SECURITY_TOKEN = 'pastebin11451419'; // any string , strlen(PASTEBIN_SECURITY_TOKEN) == 16
const PASTEBIN_CRON_TOKEN = '123456'; // any string , strlen(PASTEBIN_CRON_TOKEN) <= 1024

// ====== Others ======
const PASTEBIN_VERSION = 'v2.0 (Beta 2106)';
const SITE_URL = '';

error_reporting(E_ALL);
$_ERROR = array();