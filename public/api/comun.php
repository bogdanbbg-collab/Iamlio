<?php
// Funcții comune pentru scripturile din api/. Datele stau în api/data/, pe care serverul nu îl servește direct.

const DATA_DIR = __DIR__ . '/data';

function data_path($name)
{
    if (!is_dir(DATA_DIR)) {
        mkdir(DATA_DIR, 0750, true);
    }
    return DATA_DIR . '/' . $name;
}

function send_json($code, $body)
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
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
function lock_resource($name)
{
    $handle = fopen(data_path($name . '.lock'), 'c');
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
