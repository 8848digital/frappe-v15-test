import json
from urllib.parse import urlparse

import frappe
from frappe import sbool
from frappe.utils.response import Response

from .frappeclient import FrappeClient


class PushNotification:
	project_name = ""

	@staticmethod
	def set_project(project_name: str) -> None:
		"""
		Set the project name.

		:param project_name:  (str) The name of the project.
		:return:
		"""
		PushNotification.project_name = project_name

	def add_token(self, user_id: str, token: str) -> tuple[bool, str]:
		"""
		Add a token for a user.

		:param user_id: (str) The ID of the user. This should be user's unique identifier.
		:param token: (str) The token to be added.
		:return: tuple[bool, str] First element is the success status, second element is the message.
		"""
		data = self._send_post_request(
			"notification_relay.api.token.add", {"user_id": user_id, "fcm_token": token}
		)
		return data["success"], data["message"]

	def remove_token(self, user_id: str, token: str) -> tuple[bool, str]:
		"""
		Remove a token for a user.

		:param user_id: (str) The ID of the user. This should be user's unique identifier.
		:param token: (str) The token to be removed.
		:return: tuple[bool, str] First element is the success status, second element is the message.
		"""
		data = self._send_post_request(
			"notification_relay.api.token.remove", {"user_id": user_id, "fcm_token": token}
		)
		return data["success"], data["message"]

	def add_topic(self, topic_name: str) -> bool:
		"""
		Add a notification topic.

		:param topic_name: (str) The name of the topic.
		:return: bool True if successful, False otherwise.
		"""
		data = self._send_post_request("notification_relay.api.topic.add", {"topic_name": topic_name})
		return data["success"]

	# Remove Topic
	def remove_topic(self, topic_name: str) -> bool:
		"""
		Remove a notification topic.

		:param topic_name: (str) The name of the topic.
		:return: bool True if successful, False otherwise.
		"""
		data = self._send_post_request("notification_relay.api.topic.remove", {"topic_name": topic_name})
		return data["success"]

	def subscribe_topic(self, user_id: str, topic_name: str) -> bool:
		"""
		Subscribe a user to a topic.

		:param user_id: (str) The ID of the user. This should be user's unique identifier.
		:param topic_name: (str) The name of the topic. This topic should be already created.
		:return:
		"""
		data = self._send_post_request(
			"notification_relay.api.topic.subscribe", {"user_id": user_id, "topic_name": topic_name}
		)
		return data["success"]

	# Unsubscribe Topic (User)
	def unsubscribe_topic(self, user_id: str, topic_name: str) -> bool:
		"""
		Unsubscribe a user from a topic.

		:param user_id: (str) The ID of the user. This should be user's unique identifier.
		:param topic_name: (str) The name of the topic. This topic should be already created.
		:return: bool True if successful, False otherwise.
		"""
		data = self._send_post_request(
			"notification_relay.api.topic.unsubscribe", {"user_id": user_id, "topic_name": topic_name}
		)
		return data["success"]

	def send_notification_to_user(
		self,
		user_id: str,
		title: str,
		body: str,
		link: str = None,
		data=None,
		truncate_body: bool = False,
	) -> bool:
		"""
		Send notification to a user.

		:param user_id: (str) The ID of the user. This should be user's unique identifier.
		:param title: (str) The title of the notification.
		:param body: (str) The body of the notification. At max 1000 characters.
		:param link: (str) The link to be opened when the notification is clicked.
		:param data: (dict) The data to be sent with the notification. This can be used to provide extra information while dealing with in-app notifications.
		:param truncate_body: (bool) Whether to truncate the body or not. If True, the body will be truncated to 1000 characters.
		:return: bool True if the request queued successfully, False otherwise.
		"""
		if data is None:
			data = {}
		if link is not None and link != "":
			data["click_action"] = link
		if len(body) > 1000:
			if truncate_body:
				body = body[:1000]
			else:
				raise Exception("Body should be at max 1000 characters")
		response_data = self._send_post_request(
			"notification_relay.api.send_notification.user",
			{"user_id": user_id, "title": title, "body": body, "data": json.dumps(data)},
		)
		return response_data["success"]

	def send_notification_to_topic(
		self,
		topic_name: str,
		title: str,
		body: str,
		link: str = None,
		data=None,
		truncate_body: bool = False,
	) -> bool:
		"""
		Send notification to a notification topic.

		:param topic_name: (str) The name of the topic. This topic should be already created.
		:param title: (str) The title of the notification.
		:param body: (str) The body of the notification. At max 1000 characters.
		:param link: (str) The link to be opened when the notification is clicked.
		:param data: (dict) The data to be sent with the notification. This can be used to provide extra information while dealing with in-app notifications.
		:param truncate_body: (bool) Whether to truncate the body or not. If True, the body will be truncated to 1000 characters.
		:return:  bool True if the request queued successfully, False otherwise.
		"""
		if data is None:
			data = {}
		if link is not None and link != "":
			data["click_action"] = link
		if len(body) > 1000:
			if truncate_body:
				body = body[:1000]
			else:
				raise Exception("Body should be at max 1000 characters")
		response_data = self._send_post_request(
			"notification_relay.api.send_notification.topic",
			{"topic_name": topic_name, "title": title, "body": body, "data": json.dumps(data)},
		)
		return response_data["success"]

	def is_enabled(self) -> bool:
		"""
		Check whether the push notification relay is enabled or not.

		:return: bool True if enabled, False otherwise.
		"""
		return sbool(
			frappe.db.get_single_value("Push Notification Settings", "enable_push_notification_relay")
		)

	def _get_credential(self) -> tuple[str, str]:
		"""
		Register & Get the API key and secret from the central relay server.
		Also store the API key and secret in the database for future use.

		NOTE: This method is private and should not be called directly.

		:return: tuple[str, str] The API key and secret.
		"""
		notification_settings = frappe.get_doc("Push Notification Settings")
		if notification_settings.api_key and notification_settings.api_secret:
			return notification_settings.api_key, notification_settings.api_secret
		else:
			# Generate new credentials
			token = frappe.generate_hash(length=48)
			# store the token in the redis cache
			frappe.cache().set_value(f"{self._get_site_name}:push_relay_registration_token", token, ex=600)
			body = {
				"endpoint": self._get_site_name,
				"protocol": self._get_site_protocol,
				"port": self._get_site_port,
				"token": token,
				"webhook_route": "/api/method/frappe.push_notification.auth_webhook",
			}
			response = self._send_post_request("notification_relay.api.auth.get_credential", body, False)
			success = response["success"]
			if not success:
				raise Exception(response["message"])
			notification_settings.api_key = response["credentials"]["api_key"]
			notification_settings.api_secret = response["credentials"]["api_secret"]
			notification_settings.save(ignore_permissions=True)
			return notification_settings.api_key, notification_settings.api_secret

	def _send_post_request(self, method: str, params: dict, use_authentication: bool = True):
		"""
		Send a POST request to the central relay server.

		NOTE: This method is private and should not be called directly.

		:param method: (str) The method to be called on the central relay server.
		:param params: (dict) The parameters to be sent with the request.
		:param use_authentication: (bool) Whether to use authentication or not.
		:return: tuple[bool, dict] First element is the success status of request, second element is the response data.
		"""

		if not self.is_enabled():
			raise Exception("Push Notification Relay is not enabled")

		relay_server_endpoint = frappe.conf.get("push_relay_server_url")
		if use_authentication:
			api_key, api_secret = self._get_credential()
			client = FrappeClient(relay_server_endpoint, api_key=api_key, api_secret=api_secret)
		else:
			client = FrappeClient(relay_server_endpoint)
		params["project_name"] = PushNotification.project_name
		params["site_name"] = self._get_site_name
		return client.post_api(method, params)

	# Helper methods to fetch properties
	@property
	def _get_site_name(self) -> str:
		return urlparse(frappe.utils.get_url()).hostname

	@property
	def _get_site_protocol(self) -> str:
		return urlparse(frappe.utils.get_url()).scheme

	@property
	def _get_site_port(self) -> str:
		site_uri = urlparse(frappe.utils.get_url())
		if site_uri.port is not None:
			return str(site_uri.port)
		return ""


# Webhook which will be called by the central relay server for authentication
@frappe.whitelist(allow_guest=True, methods=["GET"])
def auth_webhook():
	token = frappe.cache().get_value(f"{frappe.local.site}:push_relay_registration_token")
	response = Response()
	response.mimetype = "text/plain; charset=UTF-8"

	if token is None or token == "":
		response.data = ""
		response.status_code = 401
		return response

	response.data = token
	response.status_code = 200
	return response


# Subscribe and Unsubscribe API
@frappe.whitelist(methods=["POST"])
def subscribe(fcm_token: str):
	success, message = PushNotification().add_token(frappe.session.user, fcm_token)
	return {"success": success, "message": message}


@frappe.whitelist(methods=["POST"])
def unsubscribe(fcm_token: str):
	success, message = PushNotification().remove_token(frappe.session.user, fcm_token)
	return {"success": success, "message": message}
