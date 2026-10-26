<?php
// Previzualizarea protejată a poveștilor personalizate neaprobate.
//
// Poveștile neaprobate NU stau în partea publică a site-ului, ci în api/data/previzualizare/<id>/, pe care serverul
// nu îl servește direct. Le poate citi doar cine a introdus parola de previzualizare (secretul PREVIEW_PASSWORD
// din GitHub; pe server stă doar o amprentă cu sare a ei, în api/data/previzualizare.json).
//
// POST (parola=…)          → verifică parola și pune un cookie de sesiune (12 ore), HttpOnly, Secure, SameSite=Strict
// GET ?stare=1             → {"autentificat": true|false}
// GET ?id=<id>&f=<fișier>  → fișierul poveștii (story.json, imagini, voce), doar cu sesiune validă
require __DIR__ . '/comun.php';

const SESSION_SECONDS = 43200;
const COOKIE = 'iamlio_previzualizare';
const MAX_FAILED_PER_HOUR = 10;

header('X-Robots-Tag: noindex, nofollow');

function session_valid()
{
    $value = isset($_COOKIE[COOKIE]) ? (string) $_COOKIE[COOKIE] : '';
    if (!preg_match('/^(\d+)\.([a-f0-9]{64})$/', $value, $m)) {
        return false;
    }
    $expected = hash_hmac('sha256', 'previzualizare|' . $m[1], secret_key());
    return (int) $m[1] > time() && hash_equals($expected, $m[2]);
}

function password_ok($password)
{
    $config = read_json_file(data_path('previzualizare.json'));
    if (empty($config['salt']) || empty($config['hash']) || $password === '') {
        return false;
    }
    return hash_equals((string) $config['hash'], hash('sha256', $config['salt'] . $password));
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'POST') {
    // limită de încercări greșite pe adresă, ca parola să nu poată fi ghicită prin încercări repetate
    $lock = lock_resource('previzualizare');
    $file = data_path('previzualizare-incercari.json');
    $now = time();
    $attempts = array_filter(read_json_file($file), function ($entry) use ($now) {
        return is_array($entry) && isset($entry[0], $entry[1]) && $now - $entry[0] < 3600;
    });
    $who = visitor_mark('previzualizare');
    $failed = isset($attempts[$who]) ? (int) $attempts[$who][1] : 0;
    if ($failed >= MAX_FAILED_PER_HOUR) {
        send_json(429, ['error' => 'prea multe încercări; mai încearcă peste o oră']);
    }
    if (!password_ok(isset($_POST['parola']) ? (string) $_POST['parola'] : '')) {
        $attempts[$who] = [isset($attempts[$who]) ? $attempts[$who][0] : $now, $failed + 1];
        write_json_atomic($file, (object) $attempts);
        sleep(1);
        send_json(401, ['error' => 'parolă greșită']);
    }
    $expires = $now + SESSION_SECONDS;
    $secure = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
    setcookie(COOKIE, $expires . '.' . hash_hmac('sha256', 'previzualizare|' . $expires, secret_key()), [
        'expires' => $expires, 'path' => '/', 'secure' => $secure, 'httponly' => true, 'samesite' => 'Strict',
    ]);
    send_json(200, ['autentificat' => true]);
}

if ($method !== 'GET') {
    header('Allow: GET, POST');
    send_json(405, ['error' => 'metodă nepermisă']);
}

if (isset($_GET['stare'])) {
    send_json(200, ['autentificat' => session_valid()]);
}

if (!session_valid()) {
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
