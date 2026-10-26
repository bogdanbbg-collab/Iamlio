<?php
// Previzualizarea protejată a poveștilor personalizate neaprobate.
//
// Poveștile neaprobate NU stau în partea publică a site-ului, ci în api/data/previzualizare/<id>/, pe care serverul
// nu îl servește direct. Le poate citi doar administratorul, după autentificare (aceeași parolă ca la panoul
// de administrare, secretul ADMIN_PASSWORD din GitHub; vezi comun.php).
//
// POST (parola=…)          → autentificare (sesiune de 12 ore, cookie HttpOnly, Secure, SameSite=Strict)
// GET ?stare=1             → {"autentificat": true|false}
// GET ?id=<id>&f=<fișier>  → fișierul poveștii (story.json, imagini, voce), doar cu sesiune validă
require __DIR__ . '/comun.php';

header('X-Robots-Tag: noindex, nofollow');

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'POST') {
    admin_login();
}

if ($method !== 'GET') {
    header('Allow: GET, POST');
    send_json(405, ['error' => 'metodă nepermisă']);
}

if (isset($_GET['stare'])) {
    send_json(200, ['autentificat' => admin_session_valid()]);
}

if (!admin_session_valid()) {
    send_json(401, ['error' => 'previzualizarea cere parola']);
}

$id = isset($_GET['id']) ? (string) $_GET['id'] : '';
$name = isset($_GET['f']) ? strtok((string) $_GET['f'], '?') : '';  // „images/x.webp?v=…” → „images/x.webp”
$allowed = '#^(story\.json|images/[a-z0-9][a-z0-9-]*\.(webp|png|jpe?g)|audio/manifest\.json|audio/(feminin|masculin)/[a-z0-9-]+\.mp3)$#';
if (!preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/', $id) || !preg_match($allowed, $name)) {
    send_json(404, ['error' => 'fișier necunoscut']);
}
$root = realpath(data_path('previzualizare/' . $id));
$path = $root ? realpath($root . '/' . $name) : false;
if (!$root || !$path || strpos($path, $root . DIRECTORY_SEPARATOR) !== 0 || !is_file($path)) {
    send_json(404, ['error' => 'fișier necunoscut']);
}

$types = ['json' => 'application/json; charset=utf-8', 'webp' => 'image/webp', 'png' => 'image/png',
          'jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'mp3' => 'audio/mpeg'];
$size = filesize($path);
header('Content-Type: ' . $types[strtolower(pathinfo($path, PATHINFO_EXTENSION))]);
header('Cache-Control: private, no-store');
header('X-Content-Type-Options: nosniff');
header('Accept-Ranges: bytes');

// Safari pe iPhone cere fișierele audio pe bucăți (Range); fără asta nu le poate reda.
$start = 0;
$end = $size - 1;
if (isset($_SERVER['HTTP_RANGE']) && preg_match('/^bytes=(\d*)-(\d*)$/', $_SERVER['HTTP_RANGE'], $m)) {
    if ($m[1] === '' && $m[2] !== '') {
        $start = max(0, $size - (int) $m[2]);
    } else {
        $start = (int) $m[1];
        $end = $m[2] !== '' ? min((int) $m[2], $size - 1) : $size - 1;
    }
    if ($start > $end || $start >= $size) {
        header('Content-Range: bytes */' . $size);
        http_response_code(416);
        exit;
    }
    http_response_code(206);
    header("Content-Range: bytes $start-$end/$size");
}
header('Content-Length: ' . ($end - $start + 1));
$handle = fopen($path, 'rb');
fseek($handle, $start);
$left = $end - $start + 1;
while ($left > 0 && !feof($handle)) {
    $chunk = fread($handle, min(65536, $left));
    echo $chunk;
    $left -= strlen($chunk);
}
fclose($handle);
