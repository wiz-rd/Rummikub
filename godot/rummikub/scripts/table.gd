extends Control


func _on_username_ready() -> void:
	# setup the username once the node loads
	$UsernamePadding/Username.text = SessionHandler.username
