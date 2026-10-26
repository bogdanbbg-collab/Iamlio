<?php
// Funcții comune pentru scripturile din api/. Datele stau în api/data/, pe care serverul nu îl servește direct.

const DATA_DIR = __DIR__ . '/data';
const ADMIN_COOKIE = 'iamlio_admin';
const ADMIN_SESSION_SECONDS = 43200; // 12 ore
const ADMIN_MAX_FAILED_PER_HOUR = 10;

date_default_timezone_set('Europe/Bucharest'); // „azi” pentru statistici înseamnă ziua din România

function data_path($name)
{
    if (!is_dir(DATA_DIR)) {
        mkdir(DATA_DIR, 0750, true);
    }
    return DATA_DIR . '/' . $name;
}

function send_json($code, $body)
{
    if ($code >= 500) {
        record_error('server', isset($body['error']) ? (string) $body['error'] : 'eroare ' . $code, '', 0);
    }
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('Referrer-Policy: strict-origin-when-cross-origin');
    header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'");
    echo json_encode($body, JSON_UNESCAPED_UNICODE);
    exit;
}

// Cheia secretă a serverului (creată la prima nevoie, nu e în repository și nu se urcă prin FTP).
function secret_key()
{
    $file = data_path('cheie.txt');
    $key = is_file($file) ? trim((string) file_get_contents($file)) : '';
    if (strlen($key) < 64) {
        $key = bin2hex(random_bytes(32));
        file_put_contents($file, $key, LOCK_EX);
        @chmod($file, 0600);
    }
    return $key;
}

function read_json_file($file)
{
    $data = is_file($file) ? json_decode((string) file_get_contents($file), true) : [];
    return is_array($data) ? $data : [];
}

// Scriere atomică: fișier temporar + rename, ca o eroare să nu lase niciodată un fișier pe jumătate scris.
function write_json_atomic($file, $data)
{
    $json = json_encode($data, JSON_UNESCAPED_UNICODE);
    if ($json === false) {
        return false;
    }
    $tmp = $file . '.' . bin2hex(random_bytes(4)) . '.tmp';
    if (file_put_contents($tmp, $json, LOCK_EX) !== strlen($json)) {
        @unlink($tmp);
        return false;
    }
    if (!rename($tmp, $file)) {
        @unlink($tmp);
        return false;
    }
    return true;
}

// Blochează (exclusiv) o resursă pe durata unei operații citește-modifică-scrie.
// Cu $wait = false nu așteaptă: întoarce null dacă altă cerere scrie chiar acum (o citire poate merge mai departe,
// fișierele se scriu atomic, deci se citesc mereu întregi).
function lock_resource($name, $wait = true)
{
    $handle = fopen(data_path($name . '.lock'), 'c');
    if ($handle !== false && !$wait) {
        if (flock($handle, LOCK_EX | LOCK_NB)) {
            return $handle;
        }
        fclose($handle);
        return null;
    }
    if ($handle === false || !flock($handle, LOCK_EX)) {
        send_json(500, ['error' => 'serverul este ocupat, încearcă din nou']);
    }
    return $handle;
}

// Amprentă a vizitatorului: HMAC cu cheia secretă, schimbată zilnic. Adresa IP nu se salvează.
function visitor_mark($purpose)
{
    $key = secret_key() . '|' . gmdate('Y-m-d');
    return hash_hmac('sha256', $purpose . '|' . ($_SERVER['REMOTE_ADDR'] ?? ''), $key);
}

// Doar familia browserului și tipul dispozitivului (ex. „Safari · telefon”), niciodată textul complet al browserului.
function browser_family()
{
    $agent = (string) ($_SERVER['HTTP_USER_AGENT'] ?? '');
    $name = 'alt browser';
    foreach (['Edg/' => 'Edge', 'SamsungBrowser' => 'Samsung', 'Firefox/' => 'Firefox', 'FxiOS' => 'Firefox',
              'CriOS' => 'Chrome', 'Chrome/' => 'Chrome', 'Safari/' => 'Safari'] as $needle => $label) {
        if (strpos($agent, $needle) !== false) {
            $name = $label;
            break;
        }
    }
    $device = preg_match('/iPad|Tablet/i', $agent) ? 'tabletă' : (preg_match('/Mobi|iPhone|Android/i', $agent) ? 'telefon' : 'calculator');
    return $name . ' · ' . $device;
}

// ---------- erorile (din browsere și de pe server), pentru panoul de administrare ----------

const ERROR_KEEP_DAYS = 14;
const ERROR_MAX_GROUPS = 300;
const ERROR_MAX_PER_DAY = 1000;

function clip($text, $length)
{
    $text = trim((string) preg_replace('/\s+/u', ' ', (string) $text));
    if (!function_exists('mb_strlen')) { // extensia mbstring lipsește pe unele servere
        return strlen($text) > $length ? substr($text, 0, $length) . '…' : $text;
    }
    return mb_strlen($text) > $length ? mb_substr($text, 0, $length) . '…' : $text;
}

// Notează o eroare, grupată după tip, mesaj și loc. Nu așteaptă niciodată după alt proces și nu aruncă erori.
function record_error($type, $message, $source, $line, $page = '')
{
    static $busy = false;
    if ($busy) {
        return false;
    }
    $busy = true;
    $saved = false;
    $handle = @fopen(DATA_DIR . '/erori.lock', 'c');
    if ($handle && flock($handle, LOCK_EX | LOCK_NB)) {
        $file = DATA_DIR . '/erori.json';
        $data = read_json_file($file);
        $today = date('Y-m-d');
        $groups = isset($data['grupuri']) && is_array($data['grupuri']) ? $data['grupuri'] : [];
        $daily = isset($data['zi']) && $data['zi'] === $today ? (int) ($data['azi'] ?? 0) : 0;
        if ($daily < ERROR_MAX_PER_DAY) {
            $message = clip($message, 300);
            $source = clip(preg_replace('#^https?://[^/]+/#', '', (string) $source), 160);
            $page = clip(preg_replace('#^https?://[^/]+/#', '', (string) $page), 160);
            $key = substr(sha1($type . '|' . $message . '|' . $source . '|' . (int) $line), 0, 12);
            $now = date('c');
            $group = isset($groups[$key]) && is_array($groups[$key]) ? $groups[$key] : [
                'tip' => $type, 'mesaj' => $message, 'sursa' => $source, 'linie' => (int) $line,
                'numar' => 0, 'prima' => $now, 'pagini' => [], 'browsere' => [],
            ];
            $group['numar']++;
            $group['ultima'] = $now;
            if ($page !== '' && !in_array($page, $group['pagini'], true) && count($group['pagini']) < 5) {
                $group['pagini'][] = $page;
            }
            $family = $type === 'server' ? 'server' : browser_family();
            $group['browsere'][$family] = (isset($group['browsere'][$family]) ? (int) $group['browsere'][$family] : 0) + 1;
            $groups[$key] = $group;
            $limit = strtotime('-' . ERROR_KEEP_DAYS . ' days');
            $groups = array_filter($groups, function ($g) use ($limit) {
                return is_array($g) && isset($g['ultima']) && strtotime($g['ultima']) >= $limit;
            });
            uasort($groups, function ($a, $b) { return strcmp($b['ultima'], $a['ultima']); });
            $groups = array_slice($groups, 0, ERROR_MAX_GROUPS, true);
            $saved = write_json_atomic($file, ['grupuri' => (object) $groups, 'zi' => $today, 'azi' => $daily + 1]);
        }
        flock($handle, LOCK_UN);
    }
    if ($handle) {
        fclose($handle);
    }
    $busy = false;
    return $saved;
}

// Erorile PHP (avertismente și erori fatale) ajung și ele în panoul de administrare.
set_error_handler(function ($severity, $message, $file, $line) {
    if (error_reporting() & $severity) {
        record_error('server', $message, basename((string) $file), $line, $_SERVER['SCRIPT_NAME'] ?? '');
    }
    return false; // PHP le tratează mai departe, ca de obicei
});
register_shutdown_function(function () {
    $error = error_get_last();
    if ($error && in_array($error['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR], true)) {
        record_error('server', $error['message'], basename((string) $error['file']), $error['line'], $_SERVER['SCRIPT_NAME'] ?? '');
    }
});

// ---------- administratorul: o singură parolă (secretul ADMIN_PASSWORD din GitHub) ----------
// Pe server stă doar o amprentă cu sare a parolei, în api/data/parola.json. Aceeași sesiune deschide
// panoul de administrare și previzualizarea poveștilor personalizate neaprobate.

function admin_session_valid()
{
    $value = isset($_COOKIE[ADMIN_COOKIE]) ? (string) $_COOKIE[ADMIN_COOKIE] : '';
    if (!preg_match('/^(\d+)\.([a-f0-9]{64})$/', $value, $m)) {
        return false;
    }
    $expected = hash_hmac('sha256', 'admin|' . $m[1], secret_key());
    return (int) $m[1] > time() && hash_equals($expected, $m[2]);
}

function admin_password_ok($password)
{
    $config = read_json_file(data_path('parola.json'));
    if (empty($config['salt']) || empty($config['hash']) || $password === '') {
        return false;
    }
    return hash_equals((string) $config['hash'], hash('sha256', $config['salt'] . $password));
}

function admin_cookie($value, $expires)
{
    $secure = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
    setcookie(ADMIN_COOKIE, $value, [
        'expires' => $expires, 'path' => '/', 'secure' => $secure, 'httponly' => true, 'samesite' => 'Strict',
    ]);
}

// POST parola=… → sesiune de 12 ore. Limită de încercări greșite pe adresă, ca parola să nu poată fi ghicită.
function admin_login()
{
    $lock = lock_resource('autentificare');
    $file = data_path('autentificare-incercari.json');
    $now = time();
    $attempts = array_filter(read_json_file($file), function ($entry) use ($now) {
        return is_array($entry) && isset($entry[0], $entry[1]) && $now - $entry[0] < 3600;
    });
    $who = visitor_mark('autentificare');
    $failed = isset($attempts[$who]) ? (int) $attempts[$who][1] : 0;
    if ($failed >= ADMIN_MAX_FAILED_PER_HOUR) {
        send_json(429, ['error' => 'prea multe încercări; mai încearcă peste o oră']);
    }
    if (!admin_password_ok(isset($_POST['parola']) ? (string) $_POST['parola'] : '')) {
        $attempts[$who] = [isset($attempts[$who]) ? $attempts[$who][0] : $now, $failed + 1];
        write_json_atomic($file, (object) $attempts);
        sleep(1);
        send_json(401, ['error' => 'parolă greșită']);
    }
    $expires = $now + ADMIN_SESSION_SECONDS;
    admin_cookie($expires . '.' . hash_hmac('sha256', 'admin|' . $expires, secret_key()), $expires);
    send_json(200, ['autentificat' => true]);
}

function admin_logout()
{
    admin_cookie('', time() - 3600);
    send_json(200, ['autentificat' => false]);
}
