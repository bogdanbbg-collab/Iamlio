<?php
// „Ți-a plăcut povestea?” de la finalul fiecărei povești: 1 = 😐 așa și așa, 2 = 🙂 da, 3 = 😍 foarte mult.
// POST ?id=<id>&nota=<1|2|3> → {"multumim": true, "numarat": true/false}
//
// Se păstrează doar totalurile pe poveste (văzute în panoul de administrare). Ca un copil să nu voteze de zeci de
// ori, aceeași adresă contează o dată pe zi pentru o poveste (amprentă HMAC, ca la contor, ștearsă după o zi);
// adresa de internet nu se salvează. Votul administratorului nu se numără.
require __DIR__ . '/comun.php';

const VOTE_WINDOW = 86400;
const MAX_RECENT_VOTES = 20000;

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
    header('Allow: POST');
    send_json(405, ['error' => 'metodă nepermisă']);
}
$id = isset($_GET['id']) ? (string) $_GET['id'] : '';
$vote = isset($_GET['nota']) ? (string) $_GET['nota'] : '';
if (!preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/', $id) || !isset(public_story_ids()[$id])) {
    send_json(404, ['error' => 'poveste necunoscută']);
}
if (!in_array($vote, ['1', '2', '3'], true)) {
    send_json(400, ['error' => 'nota trebuie să fie 1, 2 sau 3']);
}

$lock = lock_resource('pareri');
$file = data_path('pareri.json');
$stored = read_json_file($file);
$totals = isset($stored['totaluri']) && is_array($stored['totaluri']) ? $stored['totaluri'] : [];
$recent = isset($stored['recente']) && is_array($stored['recente']) ? $stored['recente'] : [];
$now = time();
$recent = array_filter($recent, function ($time) use ($now) {
    return is_int($time) && $now - $time < VOTE_WINDOW;
});

$who = visitor_mark('parere|' . $id);
$counted = !isset($recent[$who]) && count($recent) < MAX_RECENT_VOTES && !admin_session_valid();
if ($counted) {
    $recent[$who] = $now;
    $story = isset($totals[$id]) && is_array($totals[$id]) ? $totals[$id] : [];
    $story[$vote] = (int) ($story[$vote] ?? 0) + 1;
    $totals[$id] = $story;
}
if (!write_json_atomic($file, ['totaluri' => (object) $totals, 'recente' => (object) $recent])) {
    send_json(500, ['error' => 'părerea nu a putut fi salvată']);
}
send_json(200, ['multumim' => true, 'numarat' => $counted]);
