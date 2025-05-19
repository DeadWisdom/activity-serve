from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["admin"])


@router.get("/admin", response_class=HTMLResponse)
async def admin_ui():
    """Return a simple HTML admin UI shell."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Activity Serve Admin</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                color: #333;
            }
            .placeholder {
                background-color: #f5f5f5;
                padding: 20px;
                border-radius: 5px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Activity Serve Admin</h1>
            <div class="placeholder">
                <p>This is a placeholder for the admin UI. Future versions will include a full admin interface.</p>
                <p>You can use this space to build a custom admin interface for your Activity Serve instance.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content