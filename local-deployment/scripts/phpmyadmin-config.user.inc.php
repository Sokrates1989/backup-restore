<?php

$host = getenv('PMA_HOST') ?: 'test-mysql';
$port = getenv('PMA_PORT') ?: '3306';
$user = getenv('PMA_USER') ?: 'root';
$password = getenv('PMA_PASSWORD') ?: '';

$i = 1;
$cfg['Servers'][$i]['auth_type'] = 'config';
$cfg['Servers'][$i]['host'] = $host;
$cfg['Servers'][$i]['port'] = $port;
$cfg['Servers'][$i]['user'] = $user;
$cfg['Servers'][$i]['password'] = $password;
$cfg['Servers'][$i]['AllowNoPassword'] = true;

