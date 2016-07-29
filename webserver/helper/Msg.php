<?php

namespace Poketrainer\helper;

class Msg extends Helper {

	const ERROR = 1;
	const MSG = 2;

	private static function assignSession() {
		if (!isset($_SESSION["msg"])) {
			$_SESSION["msg"] = "";
		}
		if (!isset($_SESSION["err"])) {
			$_SESSION["err"] = "";
		}
	}

	public static function set($message, $type = self::MSG) {
		self::assignSession();
		if($type == self::MSG) {
			$identifier = "msg";
		} else if($type == self::ERROR) {
			$identifier = "err";
		} else {
			throw new \Exception("Unknown type of message");
		}
		$_SESSION[$identifier] .= "<li>$message</li>";
	}

	public static function get() {
		self::assignSession();
		ob_start();
		if($_SESSION['msg']) {
			?>
			<div class="row">
				<div class="col-lg-12">
					<div class="panel panel-info">
						<div class="panel-heading">
							<?= Lng::translate("Info") ?>
						</div>
						<div class="panel-body">
							<ul>
							<?= $_SESSION['msg'] ?>
							</ul>
						</div>
					</div>
				</div>
			</div>
			<?php
			$_SESSION['msg'] = "";
		}
		if($_SESSION['err']) {
			?>
			<div class="row">
				<div class="col-lg-12">
					<div class="panel panel-danger">
						<div class="panel-heading">
							<?= Lng::translate("Error") ?>
						</div>
						<div class="panel-body">
							<ul>
							<?= $_SESSION['err'] ?>
							</ul>
						</div>
					</div>
				</div>
			</div>
			<?php
			$_SESSION['err'] = "";
		}
		return ob_get_clean();
	}

}