<?php
// PHP-Reverse-Proxy fuer Infomaniak Managed Hosting.
//
// Pro Subdomain in den jeweiligen Web-Root legen und $BACKEND auf den Port der
// Stufe setzen (siehe docs/DEPLOYMENT.md):
//
//   dashboard-projekte.ch      -> 127.0.0.1:8020 (prod)
//   test.dashboard-projekte.ch -> 127.0.0.1:8021 (test)
//   int.dashboard-projekte.ch  -> 127.0.0.1:8022 (int)
//   dev.dashboard-projekte.ch  -> 127.0.0.1:8023 (dev)
//
// Gemeinsam mit der beiliegenden .htaccess deployen (leitet alle Requests hierher).

$BACKEND = 'http://127.0.0.1:8020';   // <-- pro Umgebung anpassen

$target = $BACKEND . ($_SERVER['REQUEST_URI'] ?? '/');
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

$ch = curl_init($target);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HEADER, true);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
curl_setopt($ch, CURLOPT_TIMEOUT, 120);   // LLM-Calls koennen dauern

// Request-Header durchreichen (Host weglassen – Backend bindet lokal)
$headers = [];
foreach (getallheaders() as $k => $v) {
    if (strtolower($k) === 'host') {
        continue;
    }
    $headers[] = "$k: $v";
}
$headers[] = 'X-Forwarded-Proto: https';
$headers[] = 'X-Forwarded-For: ' . ($_SERVER['REMOTE_ADDR'] ?? '');
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

// Request-Body bei schreibenden Methoden
if (in_array($method, ['POST', 'PUT', 'PATCH', 'DELETE'], true)) {
    curl_setopt($ch, CURLOPT_POSTFIELDS, file_get_contents('php://input'));
}

$response = curl_exec($ch);
if ($response === false) {
    http_response_code(502);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Bad Gateway: Backend nicht erreichbar.';
    exit;
}

$header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
$status      = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$raw_headers = substr($response, 0, $header_size);
$body        = substr($response, $header_size);
curl_close($ch);

http_response_code($status);
foreach (explode("\r\n", $raw_headers) as $line) {
    if ($line === '') {
        continue;
    }
    // Hop-by-hop- und Status-Zeilen nicht weiterreichen
    if (stripos($line, 'HTTP/') === 0) {
        continue;
    }
    if (stripos($line, 'Transfer-Encoding:') === 0) {
        continue;
    }
    if (stripos($line, 'Connection:') === 0) {
        continue;
    }
    header($line, false);
}
echo $body;
