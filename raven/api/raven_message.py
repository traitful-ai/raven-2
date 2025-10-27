import json
import time
from datetime import timedelta

import frappe
from frappe import _
from frappe.query_builder import JoinType, Order
from frappe.query_builder.functions import Coalesce, Count

from raven.api.raven_channel import create_direct_message_channel, get_peer_user_id
from raven.utils import get_channel_member, is_channel_member, track_channel_visit

import httpx

@frappe.whitelist(methods=["POST"])
def send_message(
	channel_id, text, is_reply=False, linked_message=None, json_content=None, send_silently=False
):
	channel = frappe.get_doc("Raven Channel", channel_id)
	
	# Create the user's message first
	if is_reply:
		doc = frappe.get_doc(
			{
				"doctype": "Raven Message",
				"channel_id": channel_id,
				"text": text,
				"message_type": "Text",
				"is_reply": is_reply,
				"linked_message": linked_message,
				"json": json_content,
			}
		)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Raven Message",
				"channel_id": channel_id,
				"text": text,
				"message_type": "Text",
				"json": json_content,
			}
		)

	if send_silently:
		doc.flags.send_silently = True

	doc.insert()
	
	# After the user's message is inserted, check if we need to send a bot response
	check_and_send_bot_response(channel, channel_id, text, doc)
	
	return doc


def check_and_send_bot_response(channel, channel_id, text, user_message_doc):
	"""
	Check if this is a DM with CargoWiseBot and send a response if needed
	"""
	# Check if this is a DM with a bot
	if channel.is_direct_message:
		# Get channel members to find if any are bots
		members = frappe.get_all(
			"Raven Channel Member",
			filters={"channel_id": channel_id},
			fields=["user_id"]
		)
		
		for member in members:
			# Check if this user_id is a bot (via Raven User)
			raven_user = frappe.db.get_value("Raven User", member.user_id, ["type", "bot"], as_dict=True)
			if raven_user and raven_user.type == "Bot" and raven_user.bot:
				# Get the bot name to check if it's CargoWiseBot
				bot_name = frappe.db.get_value("Raven Bot", raven_user.bot, "bot_name")
				print(f"🤖 MESSAGE TO BOT: {raven_user.bot} (name: {bot_name}) in channel {channel_id}")
				
				# Only respond if this is CargoWiseBot
				if bot_name == "CargoWiseBot":
					print(f"✅ CARGOWISE BOT DETECTED: Sending response")
					
					# Emit bot processing start event
					frappe.publish_realtime(
						"bot_processing_start",
						{
							"channel_id": channel_id,
							"bot_name": bot_name
						},
						doctype="Raven Channel",
						docname=channel_id,
						after_commit=True
					)
					
					# Send immediate "thinking" message
					thinking_message_id = send_thinking_message(channel_id, raven_user.bot)
					
					# Use frappe.enqueue to send actual response after a small delay
					frappe.enqueue(
						send_bot_response,
						channel_id=channel_id,
						bot_name=raven_user.bot,
						user_message=text,
						user_message_doc=user_message_doc,
						thinking_message_id=thinking_message_id,
						queue="short",
						timeout=30,
						is_async=True
					)
				else:
					print(f"❌ NOT CARGOWISE BOT: Ignoring message to {bot_name}")
				break


@frappe.whitelist()
def fetch_recent_files(channel_id):
	"""
	Fetches recently sent files in a channel
	Check if the user has permission to view the channel
	"""
	if not frappe.has_permission("Raven Channel", doc=channel_id):
		frappe.throw(_("You don't have permission to view this channel"), frappe.PermissionError)
	files = frappe.db.get_all(
		"Raven Message",
		filters={"channel_id": channel_id, "message_type": ["in", ["Image", "File"]]},
		fields=["name", "file", "owner", "creation", "message_type"],
		order_by="creation desc",
		limit_page_length=10,
	)

	return files


def get_messages(channel_id):

	messages = frappe.db.get_all(
		"Raven Message",
		filters={"channel_id": channel_id},
		fields=[
			"name",
			"owner",
			"creation",
			"modified",
			"text",
			"file",
			"message_type",
			"message_reactions",
			"is_reply",
			"linked_message",
			"_liked_by",
			"channel_id",
			"thumbnail_width",
			"thumbnail_height",
			"file_thumbnail",
			"link_doctype",
			"link_document",
			"replied_message_details",
			"content",
			"is_edited",
			"is_thread",
			"is_forwarded",
		],
		order_by="creation asc",
	)

	return messages


@frappe.whitelist()
def save_message(message_id, add=False):
	"""
	Save the message as a bookmark
	"""
	from frappe.desk.like import toggle_like
	import time

	toggle_like("Raven Message", message_id, add)

	liked_by = frappe.db.get_value("Raven Message", message_id, "_liked_by")

	frappe.publish_realtime(
		"message_saved",
		{
			"message_id": message_id,
			"liked_by": liked_by,
		},
		user=frappe.session.user,
	)

	return "message saved"


@frappe.whitelist()
def get_pinned_messages(channel_id):

	# check if the user has permission to view the channel
	frappe.has_permission("Raven Channel", doc=channel_id, ptype="read", throw=True)

	pinnedMessagesString = frappe.db.get_value("Raven Channel", channel_id, "pinned_messages_string")
	pinnedMessages = pinnedMessagesString.split("\n") if pinnedMessagesString else []

	return frappe.db.get_all(
		"Raven Message",
		filters={"name": ["in", pinnedMessages]},
		fields=[
			"name",
			"owner",
			"creation",
			"bot",
			"text",
			"file",
			"message_type",
			"message_reactions",
			"_liked_by",
			"channel_id",
			"thumbnail_width",
			"thumbnail_height",
			"file_thumbnail",
			"link_doctype",
			"link_document",
			"replied_message_details",
			"hide_link_preview",
			"is_bot_message",
			"content",
			"is_edited",
			"is_thread",
			"is_forwarded",
		],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_saved_messages():
	"""
	Fetches list of all messages liked by the user
	Check if the user has permission to view the message
	"""

	raven_message = frappe.qb.DocType("Raven Message")
	raven_channel = frappe.qb.DocType("Raven Channel")
	raven_channel_member = frappe.qb.DocType("Raven Channel Member")

	query = (
		frappe.qb.from_(raven_message)
		.join(raven_channel, JoinType.left)
		.on(raven_message.channel_id == raven_channel.name)
		.join(raven_channel_member, JoinType.left)
		.on(raven_channel.name == raven_channel_member.channel_id)
		.select(
			raven_message.name,
			raven_message.owner,
			raven_message.creation,
			raven_message.text,
			raven_message.channel_id,
			raven_message.file,
			raven_message.message_type,
			raven_message.message_reactions,
			raven_message._liked_by,
			raven_channel.workspace,
			raven_message.thumbnail_width,
			raven_message.thumbnail_height,
			raven_message.is_bot_message,
			raven_message.bot,
		)
		.where(raven_message._liked_by.like("%" + frappe.session.user + "%"))
		.where(
			(raven_channel.type.isin(["Open", "Public"]))
			| (raven_channel_member.user_id == frappe.session.user)
		)
		.orderby(raven_message.creation, order=Order.asc)
		.distinct()
	)  # Add DISTINCT keyword to retrieve only unique messages

	messages = query.run(as_dict=True)

	return messages


def parse_messages(messages):

	messages_with_date_header = []
	previous_message = None

	for i in range(len(messages)):
		message = messages[i]
		is_continuation = (
			previous_message
			and message["owner"] == previous_message["owner"]
			and (message["creation"] - previous_message["creation"]) < timedelta(minutes=2)
		)
		message["is_continuation"] = int(bool(is_continuation))

		if i == 0 or message["creation"].date() != previous_message["creation"].date():
			messages_with_date_header.append({"block_type": "date", "data": message["creation"].date()})

		messages_with_date_header.append({"block_type": "message", "data": message})

		previous_message = message

	return messages_with_date_header


def check_permission(channel_id):
	if frappe.get_cached_value("Raven Channel", channel_id, "type") == "Private":
		if is_channel_member(channel_id):
			pass
		elif frappe.session.user == "Administrator":
			pass
		else:
			frappe.throw(_("You don't have permission to view this channel"), frappe.PermissionError)


@frappe.whitelist()
def get_messages_with_dates(channel_id):
	check_permission(channel_id)
	messages = get_messages(channel_id)
	track_channel_visit(channel_id=channel_id, publish_event_for_user=True, commit=True)
	return parse_messages(messages)


@frappe.whitelist()
def get_unread_count_for_channels():
	"""
	Fetch all channels where the user has unread messages > 0
	"""

	channel = frappe.qb.DocType("Raven Channel")
	channel_member = frappe.qb.DocType("Raven Channel Member")
	message = frappe.qb.DocType("Raven Message")
	query = (
		frappe.qb.from_(channel)
		.left_join(channel_member)
		.on(
			(channel.name == channel_member.channel_id) & (channel_member.user_id == frappe.session.user)
		)
		.where(channel_member.user_id == frappe.session.user)
		.where(channel.is_archived == 0)
		.where(channel.is_thread == 0)
		.where(message.message_type != "System")
		.where(
			message.creation > Coalesce(channel_member.last_visit, "2000-11-11")
		)  # Only count messages after the last visit for performance
		.left_join(message)
		.on(channel.name == message.channel_id)
	)

	channels_query = (
		query.select(channel.name, channel.is_direct_message, Count(message.name).as_("unread_count"))
		.groupby(channel.name, channel.is_direct_message)
		.run(as_dict=True)
	)

	return channels_query


@frappe.whitelist()
def get_unread_count_for_channel(channel_id):
	channel_member = get_channel_member(channel_id=channel_id)
	if channel_member:
		last_timestamp = frappe.get_cached_value(
			"Raven Channel Member", channel_member["name"], "last_visit"
		)

		return frappe.db.count(
			"Raven Message",
			filters={
				"channel_id": channel_id,
				"creation": (">", last_timestamp),
				"message_type": ["!=", "System"],
			},
		)
	else:
		if frappe.get_cached_value("Raven Channel", channel_id, "type") == "Open":
			return frappe.db.count(
				"Raven Message",
				filters={
					"channel_id": channel_id,
					"message_type": ["!=", "System"],
				},
			)
		else:
			return 0


@frappe.whitelist()
def get_timeline_message_content(doctype, docname):
	channel = frappe.qb.DocType("Raven Channel")
	channel_member = frappe.qb.DocType("Raven Channel Member")
	message = frappe.qb.DocType("Raven Message")
	user = frappe.qb.DocType("User")
	query = (
		frappe.qb.from_(message)
		.select(
			message.creation,
			message.owner,
			message.name,
			message.text,
			message.file,
			channel.name.as_("channel_id"),
			channel.channel_name,
			channel.type,
			channel.is_direct_message,
			user.full_name,
			channel.is_self_message,
		)
		.join(channel)
		.on(message.channel_id == channel.name)
		.join(channel_member)
		.on(
			(message.channel_id == channel_member.channel_id) & (message.owner == channel_member.user_id)
		)
		.join(user)
		.on(message.owner == user.name)
		.where((channel.type != "Private") | (channel_member.user_id == frappe.session.user))
		.where(message.link_doctype == doctype)
		.where(message.link_document == docname)
	)
	data = query.run(as_dict=True)

	timeline_contents = []
	for log in data:

		if log.is_direct_message:
			peer_user_id = get_peer_user_id(log.channel_id, log.is_direct_message, log.is_self_message)
			if peer_user_id:
				log["peer_user"] = frappe.db.get_value("User", peer_user_id, "full_name")
		timeline_contents.append(
			{
				"icon": "share",
				"is_card": True,
				"creation": log.creation,
				"template": "send_message",
				"template_data": log,
			}
		)

	return timeline_contents


file_extensions = {
	"doc": [
		"doc",
		"docx",
		"odt",
		"ott",
		"rtf",
		"txt",
		"dot",
		"dotx",
		"docm",
		"dotm",
		"pages",
	],
	"ppt": [
		"ppt",
		"pptx",
		"odp",
		"otp",
		"pps",
		"ppsx",
		"pot",
		"potx",
		"pptm",
		"ppsm",
		"potm",
		"ppam",
		"ppa",
		"key",
	],
	"xls": [
		"xls",
		"xlsx",
		"csv",
		"ods",
		"ots",
		"xlsb",
		"xlsm",
		"xlt",
		"xltx",
		"xltm",
		"xlam",
		"xla",
		"numbers",
	],
}


@frappe.whitelist()
def get_all_files_shared_in_channel(
	channel_id, file_name=None, file_type=None, start_after=0, page_length=None
):

	# check if the user has permission to view the channel
	check_permission(channel_id)

	message = frappe.qb.DocType("Raven Message")
	user = frappe.qb.DocType("Raven User")
	file = frappe.qb.DocType("File")

	query = (
		frappe.qb.from_(message)
		.join(file)
		.on(message.name == file.attached_to_name)
		.join(user)
		.on(message.owner == user.name)
		.select(
			file.name,
			file.file_name,
			file.file_type,
			file.file_size,
			file.file_url,
			message.owner,
			message.creation,
			message.message_type,
			message.thumbnail_width,
			message.thumbnail_height,
			message.file_thumbnail,
			user.full_name,
			user.user_image,
			message.name.as_("message_id"),
		)
		.where(message.channel_id == channel_id)
	)

	# search for file name
	if file_name:
		query = query.where(file.file_name.like("%" + file_name + "%"))

	# search for file type
	if file_type:
		if file_type == "image":
			query = query.where(message.message_type == "Image")
		elif file_type == "file":
			query = query.where(message.message_type == "File")
		elif file_type == "pdf":
			query = query.where(file.file_type == "pdf")
		else:
			# Get the list of extensions for the given file type
			extensions = file_extensions.get(file_type)
			if extensions:
				query = query.where((file.file_type).isin(extensions))
	else:
		query = query.where(message.message_type.isin(["Image", "File"]))

	files = (
		query.orderby(message.creation, order=Order["desc"])
		.limit(page_length)
		.offset(start_after)
		.run(as_dict=True)
	)

	return files


@frappe.whitelist()
def get_count_for_pagination_of_files(channel_id, file_name=None, file_type=None):

	# check if the user has permission to view the channel
	check_permission(channel_id)

	message = frappe.qb.DocType("Raven Message")
	# user = frappe.qb.DocType("Raven User")
	file = frappe.qb.DocType("File")

	query = (
		frappe.qb.from_(message)
		.join(file, JoinType.left)
		.on(message.name == file.attached_to_name)
		.select(Count(message.name).as_("count"))
		.where(message.channel_id == channel_id)
	)

	# search for file name
	if file_name:
		query = query.where(file.file_name.like("%" + file_name + "%"))

	# search for file type
	if file_type:
		if file_type == "image":
			query = query.where(message.message_type == "Image")
		elif file_type == "pdf":
			query = query.where(file.file_type == "pdf")
		else:
			# Get the list of extensions for the given file type
			extensions = file_extensions.get(file_type)
			if extensions:
				query = query.where((file.file_type).isin(extensions))
	else:
		query = query.where(message.message_type.isin(["Image", "File"]))
	count = query.run(as_dict=True)

	return count[0]["count"]


@frappe.whitelist(methods=["POST"])
def forward_message(message_receivers, forwarded_message):
	"""
	Forward a message to multiple users/ or in multiple channels
	"""
	for receiver in message_receivers:
		if receiver["type"] == "User":
			# send forwarded message as a DM to the user
			# get DM channel ID, create a copy of the message and send it to the channel, change the message owner to current sender
			dm_channel_id = create_direct_message_channel(receiver["name"])
			add_forwarded_message_to_channel(dm_channel_id, forwarded_message)
		else:
			# send forwarded message to the channel
			add_forwarded_message_to_channel(receiver["name"], forwarded_message)

	return "messages forwarded"


def add_forwarded_message_to_channel(channel_id, forwarded_message):
	"""
	Forward a message to a channel - copy over the message,
	change the owner to the current user and timestamp to now,
	mark it as forwarded
	"""
	# If the forwarded message has a file, we need to remove the "fid" from the URL - this is done so that the new user can access the file
	if forwarded_message.get("file"):
		forwarded_message["file"] = forwarded_message["file"].split("?")[0]
	doc = frappe.get_doc(
		{
			"doctype": "Raven Message",
			**forwarded_message,
			"channel_id": channel_id,
			"name": None,
			"owner": frappe.session.user,
			"creation": frappe.utils.now_datetime(),
			"modified": frappe.utils.now_datetime(),
			"is_continuation": 0,
			"is_edited": 0,
			"is_reply": 0,
			"is_forwarded": 1,
			"is_thread": 0,
			"replied_message_details": None,
			"message_reactions": None,
		}
	)
	doc.insert()
	return "message forwarded"


def send_thinking_message(channel_id, bot_raven_user):
	"""
	Send an immediate "thinking" message that will be replaced later
	"""
	try:
		thinking_doc = frappe.get_doc({
			"doctype": "Raven Message",
			"channel_id": channel_id,
			"text": "🤔 Freightify AI is working on your request...",
			"message_type": "Text",
			"owner": bot_raven_user,
			"is_bot_message": 1,
			"bot": bot_raven_user
		})
		thinking_doc.insert(ignore_permissions=True)
		print(f"💭 THINKING MESSAGE SENT: {thinking_doc.name}")
		return thinking_doc.name
		
	except Exception as e:
		print(f"❌ ERROR sending thinking message: {str(e)}")
		frappe.log_error(f"Error sending thinking message: {str(e)}", "Bot Thinking Message Error")
		return None


def process_bot_file_attachments(file_content, channel_id, bot_doc):
	"""
	Process file_content array from bot API response and create file attachments
	Each file object should have: {'file_name': 'file.pdf', 'file_content': 'base64string'}
	"""
	import base64
	
	file_message_ids = []
	
	for file_obj in file_content:
		try:
			filename = file_obj.get('file_name', 'untitled_file')
			base64_string = file_obj.get('file_content', '')
			
			if not base64_string:
				print(f"⚠️ WARNING: No base64 content found for file {filename}")
				continue
				
			print(f"📎 PROCESSING FILE: {filename}")
			
			# Decode base64 content
			file_data = base64.b64decode(base64_string)
			
			# Create a file document using the same pattern as the upload_file_with_message API
			file_doc = frappe.get_doc({
				"doctype": "File",
				"file_name": filename,
				"content": file_data,
				"is_private": 1,
			})
			file_doc.insert(ignore_permissions=True)
			
			print(f"📁 FILE CREATED: {file_doc.file_url} for {filename}")
			
			# Send file message using bot's send_message method
			message_id = bot_doc.send_message(
				channel_id=channel_id,
				text=f"📎 {filename}",
				file=file_doc.file_url
			)
			
			file_message_ids.append(message_id)
			print(f"✅ FILE MESSAGE SENT: {filename} as message {message_id}")
			
		except Exception as e:
			print(f"❌ ERROR processing file {file_obj.get('file_name', 'unknown')}: {str(e)}")
			frappe.log_error(f"Error processing bot file attachment: {str(e)}", "Bot File Processing Error")
			continue
	
	return file_message_ids


def process_user_message_files(user_message_doc):
	"""
	Extract and process files attached to a user message for bot API
	Returns array of file dictionaries with file_type and file_content (base64)
	"""
	import base64
	import os
	
	files_data = []
	
	try:
		# Check if the message has a file attached
		if not user_message_doc.file:
			return files_data
			
		print(f"📎 PROCESSING FILE: {user_message_doc.file}")
		
		# Get the file document using file_url
		file_docs = frappe.get_all("File", filters={"file_url": user_message_doc.file}, limit=1)
		if not file_docs:
			print(f"❌ ERROR: File document not found for URL {user_message_doc.file}")
			return files_data
		
		file_doc = frappe.get_doc("File", file_docs[0].name)
		
		# Check file size (10MB limit = 10 * 1024 * 1024 bytes)
		max_size = 10 * 1024 * 1024
		if file_doc.file_size and file_doc.file_size > max_size:
			print(f"⚠️ WARNING: File {file_doc.file_name} is too large ({file_doc.file_size} bytes > {max_size} bytes)")
			return files_data
		
		# Get file content using Frappe's method
		try:
			file_content = file_doc.get_content()
		except Exception as e:
			print(f"❌ ERROR: Could not get file content: {str(e)}")
			return files_data
		
		if file_content:
			# Convert to base64
			base64_content = base64.b64encode(file_content).decode('utf-8')
			
			# Extract file extension for file_type
			file_name = file_doc.file_name or "unknown"
			file_extension = os.path.splitext(file_name)[1].lstrip('.').lower()
			if not file_extension:
				file_extension = "unknown"
			
			files_data.append({
				"file_name": file_name,
				"file_content": base64_content
			})
			
			print(f"✅ FILE PROCESSED: {file_name} ({len(base64_content)} chars base64, type: {file_extension})")
		
	except Exception as e:
		print(f"❌ ERROR processing user message files: {str(e)}")
		frappe.log_error(f"Error processing user message files: {str(e)}", "Bot File Processing Error")
	
	return files_data


def send_bot_response(channel_id, bot_name, user_message, user_message_doc=None, thinking_message_id=None):
	"""
	Send a bot response by calling the chat API and polling for completion
	"""
	print(f"🤖 SENDING BOT RESPONSE: Bot {bot_name} responding to '{user_message}'")
	
	# Process attached files if any
	files_data = []
	if user_message_doc:
		files_data = process_user_message_files(user_message_doc)
		if files_data:
			print(f"📎 PROCESSED {len(files_data)} file attachments for bot API")
	
	# Initialize default response text
	response_text = "Sorry, I'm having trouble processing your request right now."
	
	# Make synchronous HTTP request
	try:
		# Prepare request payload
		request_data = {
			"content": user_message
		}
		
		# Add files if any are attached
		if files_data:
			request_data["files"] = files_data
			print(f"📤 INCLUDING {len(files_data)} files in bot API request")
		
		response = httpx.post(
			f"http://52.140.80.226/api/v1/chat/{frappe.session.user}/{channel_id}/messages",
			headers={
				"Authorization": "Bearer #3re15a8$0nDoWtrAItfu7(#a70k3N",
				"Content-Type": "application/json"
			},
			json=request_data,
			timeout=10.0
		)
		response.raise_for_status()  # Raise an exception for bad status codes		
		response_data = response.json()
		print(f"📤 POST RESPONSE: {response_data}")
		
		message_id = response_data.get("message_id")
		user_id = response_data.get("user_id")
		thread_id = response_data.get("thread_id")
		
		if not message_id or not user_id or not thread_id:
			print("❌ ERROR: Missing required fields in API response")
			response_text = "Error: Invalid response from API"
		else:
			# Poll the message status until completed
			max_attempts = 30  # Maximum polling attempts
			poll_interval = 2  # Seconds between polls
			
			for attempt in range(max_attempts):
				print(f'🔄 POLLING ATTEMPT {attempt + 1}/{max_attempts}')
				try:
					status_response = httpx.get(
						f"http://52.140.80.226/api/v1/chat/{user_id}/{thread_id}/messages/{message_id}",
						headers={
							"Authorization": "Bearer #3re15a8$0nDoWtrAItfu7(#a70k3N",
							"Content-Type": "application/json"
						},
						timeout=10.0
					)
					status_response.raise_for_status()
					status_data = status_response.json()
					print(f"📥 POLL RESPONSE: {status_data}")
					
					status = status_data.get("status")
					if status == "completed":
						response_text = status_data.get("response_content", "No response content available")
						file_content = status_data.get("files", [])
						print(f"✅ POLLING COMPLETE: Got response after {attempt + 1} attempts")
						print(f"📎 FILES FOUND: {len(file_content)} files in response")
						break
					elif status == "failed":
						response_text = "Sorry, I encountered an error processing your request."
						file_content = []
						print(f"❌ POLLING FAILED: Request failed after {attempt + 1} attempts")
						break
					else:
						print(f"⏳ POLLING: Status is '{status}', continuing...")
						if attempt < max_attempts - 1:  # Don't sleep on the last attempt
							time.sleep(poll_interval)
				
				except Exception as poll_error:
					print(f"❌ ERROR during polling attempt {attempt + 1}: {str(poll_error)}")
					if attempt == max_attempts - 1:  # Last attempt
						response_text = "Sorry, I'm having trouble processing your request right now."
						break
					if attempt < max_attempts - 1:
						time.sleep(poll_interval)
			else:
				# This executes if the loop completed without breaking
				response_text = "Sorry, your request is taking longer than expected to process."
				file_content = []
				print(f"⏰ POLLING TIMEOUT: Reached maximum attempts ({max_attempts})")
				
	except Exception as e:
		print(f"❌ ERROR making HTTP request: {str(e)}")
		frappe.log_error(f"Error making HTTP request: {str(e)}", "Bot HTTP Request Error")
		response_text = "Sorry, I'm experiencing technical difficulties."
		file_content = []
	
	# Get the bot's Raven User ID
	bot_raven_user = frappe.db.get_value("Raven Bot", bot_name, "raven_user")
	if not bot_raven_user:
		print(f"❌ ERROR: Could not find raven_user for bot {bot_name}")
		return
	
	# Update the thinking message if it exists, otherwise create a new message
	try:
		# Get the bot document to use its send_message method with markdown support
		bot_doc = frappe.get_doc("Raven Bot", bot_name)
		
		# Process file attachments if any
		file_message_ids = []
		if file_content and len(file_content) > 0:
			print(f"📎 PROCESSING {len(file_content)} file attachments")
			file_message_ids = process_bot_file_attachments(file_content, channel_id, bot_doc)
		
		if thinking_message_id:
			# Replace the thinking message with the actual response using markdown
			thinking_doc = frappe.get_doc("Raven Message", thinking_message_id)
			# Convert markdown to HTML using the same method as bot.send_message
			html_text = frappe.utils.md_to_html(response_text).rstrip("\n")
			thinking_doc.text = html_text
			thinking_doc.save(ignore_permissions=True)
			frappe.db.commit()  # Ensure the change is committed
			print(f"✅ SUCCESS: Thinking message updated with bot response (markdown converted)!")
			
			# Emit bot processing end event
			print(f"🔔 EMITTING bot_processing_end for channel {channel_id} (thinking message updated)")
			frappe.publish_realtime(
				"bot_processing_end",
				{
					"channel_id": channel_id,
					"bot_name": bot_name
				},
				doctype="Raven Channel",
				docname=channel_id,
				after_commit=True
			)
			
			return {"message_id": thinking_message_id, "file_message_ids": file_message_ids}
		else:
			# Create a new message using the bot's send_message method with markdown support
			message_id = bot_doc.send_message(
				channel_id=channel_id,
				text=response_text,
				markdown=True
			)
			frappe.db.commit()  # Ensure the change is committed
			print(f"✅ SUCCESS: New bot response sent successfully with markdown support!")
			
			# Emit bot processing end event
			print(f"🔔 EMITTING bot_processing_end for channel {channel_id} (new message created)")
			frappe.publish_realtime(
				"bot_processing_end",
				{
					"channel_id": channel_id,
					"bot_name": bot_name
				},
				doctype="Raven Channel",
				docname=channel_id,
				after_commit=True
			)
			
			return {"message_id": message_id, "file_message_ids": file_message_ids}
		
	except Exception as e:
		print(f"❌ ERROR sending bot response: {str(e)}")
		frappe.log_error(f"Error sending bot response: {str(e)}", "Bot Response Error")
		
		# Emit bot processing end event even on error
		print(f"🔔 EMITTING bot_processing_end for channel {channel_id} (error occurred)")
		frappe.publish_realtime(
			"bot_processing_end",
			{
				"channel_id": channel_id,
				"bot_name": bot_name
			},
			doctype="Raven Channel",
			docname=channel_id,
			after_commit=True
		)
		
		return None
