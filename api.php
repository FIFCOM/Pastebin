<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/deprecated__fidFunctions.php");

$pastebinMode = $_REQUEST['mode'] ?? 0;
$pastebinLink = $_REQUEST['pb'] ?? 0;

if ($pastebinMode == "raw" && $pastebinLink) rawJson($pastebinLink);