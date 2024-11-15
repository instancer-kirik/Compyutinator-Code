# tracker = EmailPixelTracker()

# # Create a tracking pixel
# tracking_pixel = tracker.create_tracking_pixel()

# # Add to your email HTML
# email_html = f"""
# <html>
# <body>
#     <p>Hello,</p>
#     <p>This is an email with tracking.</p>
#     {tracking_pixel}
# </body>
# </html>
# """


# # When receiving an email
# email_content = """
# <html>
# <body>
#     <p>Some email content</p>
#     <img src="data:image/png;base64,..." width="1" height="1" />
# </body>
# </html>
# """

# tracker = EmailPixelTracker()
# tracking_pixels = tracker.detect_tracking_pixels(email_content)

# if tracking_pixels:
#     print(f"Found {len(tracking_pixels)} tracking pixels!")
#     tracker.log_tracking_attempt(
#         email_subject="Test Email",
#         sender="sender@example.com"
#     )