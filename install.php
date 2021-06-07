<?php
// FIFCOM Pastebin Installer

$installerStep = installerCheckDatabaseConnection() == 1 ? 2 : 1;

if ($installerStep == 1)
{
    $name = $_REQUEST['db-name'];
    $user = $_REQUEST['db-user'];
    $host = $_REQUEST['db-host'];
    $pwd = $_REQUEST['db-pwd'];
} else if ($installerStep == 2) {
    $admin_username = $_REQUEST['admin-username'];
}



function installerCheckDatabaseConnection() {

}

function installerWriteConfigFile($string) {

}

