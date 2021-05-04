<?php
header("Content-type:text/plain;charset=utf-8;");
require_once("config/pastebinConfig.php");

$expire = date("y") * 366 + date("m") * 31 + date("d");
echo "FIFCOM Pastebin Crontab - Current Expire Time : $expire \n";
$conn = mysqli_connect(PASTEBIN_DB_HOSTNAME, PASTEBIN_DB_USERNAME, PASTEBIN_DB_PASSWORD, PASTEBIN_DB_NAME);
if (mysqli_connect_errno()) echo "FIFCOM Pastebin MySQL Connect Error : " . mysqli_connect_error();
$result = mysqli_query($conn, "SELECT * FROM pastebin WHERE expire < '$expire'");
while ($row = mysqli_fetch_array($result)) {
    echo $row['filename'] . ".pb expired on " . $row['expire'] . "\n\n";
    if (file_exists("data/pastebin/" . $row['filename'] . ".pb")) {
        unlink("data/pastebin/" . $row['filename'] . ".pb");
        echo "Deleted : data/pastebin/" . $row['filename'] . ".pb\n";
    }
    if (file_exists("data/title/" . $row['filename'] . ".pb")) {
        unlink("data/title/" . $row['filename'] . ".pb");
        echo "Deleted : data/title/" . $row['filename'] . ".pb\n";
    }
    if (file_exists("data/info/" . $row['filename'] . ".pb")) {
        unlink("data/info/" . $row['filename'] . ".pb");
        echo "Deleted : data/info/" . $row['filename'] . ".pb\n\n";
    }
    mysqli_query($conn, "DELETE FROM pastebin WHERE filename='" . $row['filename'] . "' AND expire='" . $row['expire'] . "'");
}
echo "COMPLETED!\n";
mysqli_close($conn);