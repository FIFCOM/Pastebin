<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
session_name("PB_SSID");
session_start([
    'cookie_lifetime' => 864,
]);
$_SESSION['xx'] = 'green';
echo "123" . SID;