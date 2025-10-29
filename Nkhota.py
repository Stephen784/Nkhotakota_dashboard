import pandas as pd
import os, datetime, smtplib, ssl
from email.message import EmailMessage
from jupyter_dash import JupyterDash
from dash import dcc, html, dash_table, Input, Output, State
from dotenv import load_dotenv

# === Load environment variables for Gmail ===
load_dotenv()

WORKBOOK_PATH = r"C:/Users/user/OneDrive/Desktop/CENTRAL REGION 1ST FULLY PAID DATA (1).xlsx"
SHEET_NAME = r"NKHOTAKOTA"
COLLECTED_FILE = r"C:/Users/user/OneDrive/Desktop/district_dashboards/collected_nkhotakota.csv"
DISPLAY_FIELDS = [
    'Farmer Name', 'Contact', 'District', 'Delivery Mode',
    'Delivery Centre', 'Order No', 'Products Code', 'Products Quantity', 'Order Total Price'
]

# === Load workbook data ===
def load_and_prepare():
    df = pd.read_excel(WORKBOOK_PATH, sheet_name=SHEET_NAME, dtype=str)
    for c in DISPLAY_FIELDS:
        if c not in df.columns:
            df[c] = ""
    if "Order Total Price" in df.columns:
        def parse_price(v):
            try:
                if pd.isna(v):
                    return 0.0
                s = str(v).replace(",", "").strip()
                import re
                nums = re.findall(r'\d+(?:\.\d+)?', s)
                return sum(map(float, nums)) if nums else 0.0
            except:
                return 0.0
        df["Order Total Price"] = df["Order Total Price"].apply(parse_price)
    return df

MASTER_DF = load_and_prepare()

# === Manage collected data ===
def load_collected():
    if not os.path.exists(COLLECTED_FILE):
        pd.DataFrame(columns=["Order No", "Contact", "MarkedBy", "Timestamp", "Status"]).to_csv(COLLECTED_FILE, index=False)
        return pd.DataFrame(columns=["Order No", "Contact", "MarkedBy", "Timestamp", "Status"])
    try:
        return pd.read_csv(COLLECTED_FILE, dtype=str)
    except Exception:
        pd.DataFrame(columns=["Order No", "Contact", "MarkedBy", "Timestamp", "Status"]).to_csv(COLLECTED_FILE, index=False)
        return pd.DataFrame(columns=["Order No", "Contact", "MarkedBy", "Timestamp", "Status"])

def save_collected(df):
    df.to_csv(COLLECTED_FILE, index=False)

# === Email sync function ===
def send_csv_to_email():
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = "stephenlongwe78@gmail.com"
    subject = "Collected Orders Sync"
    body = "Attached is the latest collected.csv file."

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with open(COLLECTED_FILE, "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="csv", filename="collected.csv")

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Email send error:", e)
        return False

# === App Layout ===
app = JupyterDash(__name__)
app.title = f"LOOKUP - {SHEET_NAME}"

app.layout = html.Div(style={"backgroundColor": "#0B132B", "color": "#F0F0F0",
                              "fontFamily": "Arial, sans-serif", "padding": "20px"}, children=[

    html.H2(f"LOOKUP - {SHEET_NAME}", style={"color": "#F0F0F0", "textAlign": "center", "marginBottom": "30px"}),

    html.Div([
        dcc.Input(id="search-input", type="text", placeholder="Enter Order No or Contact",
                  style={"width": "260px", "padding": "8px", "borderRadius": "6px",
                         "border": "1px solid #444", "backgroundColor": "#2C2C3C",
                         "color": "#F0F0F0", "marginRight": "8px"}),

        html.Br(), html.Br(),

        html.Button("Search", id="search-btn", n_clicks=0,
                    style={"padding": "8px 12px", "borderRadius": "6px", "border": "none",
                           "backgroundColor": "#2196F3", "color": "#FFF",
                           "fontWeight": "bold", "cursor": "pointer", "marginRight": "10px"}),

        html.Button("Mark Delivered", id="mark-btn", n_clicks=0,
                    style={"padding": "8px 12px", "borderRadius": "6px", "border": "none",
                           "backgroundColor": "#006400", "color": "#FFF",
                           "fontWeight": "bold", "cursor": "pointer"}),

        html.Div(id="action-msg", style={"marginTop": "10px", "color": "#28A745", "fontWeight": "bold"})
    ], style={"textAlign": "left", "marginBottom": "20px"}),

    html.Div([
        html.H4("Order / Farmer Details", style={"marginBottom": "10px"}),
        dash_table.DataTable(
            id="result-table",
            columns=[{"name": c, "id": c} for c in DISPLAY_FIELDS if c != "Order Total Price"] +
                    [{"name": "Order Total Price (MWK)", "id": "Order Total Price (MWK)"}],
            data=[],
            style_table={"overflowX": "auto", "maxWidth": "100%"},
            style_header={"backgroundColor": "#2C2C3C", "color": "#F0F0F0", "fontWeight": "bold",
                          "border": "1px solid #444"},
            style_cell={"backgroundColor": "#0B132B", "color": "#F0F0F0", "padding": "6px",
                        "border": "1px solid #444", "textAlign": "left", "fontSize": "14px"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#111A35"},
                {"if": {"row_index": "even"}, "backgroundColor": "#0B132B"}
            ],
            page_size=10
        ),
        html.Div(id="collected-status", style={"marginTop": "8px", "fontWeight": "bold"}),

        # === Confirm Dialog for Undeliver ===
        dcc.ConfirmDialog(
            id="confirm-undeliver",
            message="Are you sure you want to mark this order as UNDELIVERED?"
        ),

        html.Button("Mark Undelivered", id="undeliver-btn", n_clicks=0,
                    style={"padding": "8px 12px", "borderRadius": "6px", "border": "none",
                           "backgroundColor": "#8B0000", "color": "#FFF", "fontWeight": "bold",
                           "cursor": "pointer", "marginTop": "10px"})
    ], style={"width": "100%", "marginBottom": "30px"}),

    html.H4("Delivered Orders Log", style={"marginBottom": "10px"}),

    dash_table.DataTable(
        id="collected-table",
        columns=[{"name": c, "id": c} for c in ["Order No", "Contact", "MarkedBy", "Timestamp", "Status"]],
        data=[], page_size=10,
        style_header={"backgroundColor": "#2C2C3C", "color": "#F0F0F0", "fontWeight": "bold",
                      "border": "1px solid #444"},
        style_cell={"backgroundColor": "#0B132B", "color": "#F0F0F0", "padding": "6px",
                    "border": "1px solid #444", "textAlign": "left", "fontSize": "14px"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#111A35"},
            {"if": {"row_index": "even"}, "backgroundColor": "#0B132B"}
        ],
        style_table={"overflowX": "auto", "maxWidth": "100%"}
    ),

    html.Div([
        html.Button("SYNC", id="sync-btn", n_clicks=0,
                    style={"marginTop": "20px", "padding": "10px 16px", "borderRadius": "6px",
                           "border": "none", "backgroundColor": "purple", "color": "#FFF",
                           "fontWeight": "bold", "cursor": "pointer"}),
        html.Div(id="sync-msg", style={"marginTop": "10px", "fontWeight": "bold", "color": "#FFD700"})
    ], style={"textAlign": "center", "marginTop": "20px"})
])

# === Callbacks ===
@app.callback(
    [Output("result-table", "data"), Output("collected-status", "children")],
    Input("search-btn", "n_clicks"),
    State("search-input", "value")
)
def do_search(n, query):
    if not query:
        return [], ""
    df = MASTER_DF
    q = str(query).strip()
    mask = df["Order No"].astype(str).str.contains(q, case=False, na=False) | df["Contact"].astype(str).str.contains(q, case=False, na=False)
    results = df[mask].copy()
    if results.empty:
        return [], html.Div("❌ No record found.", style={"color": "#FFA500"})
    if "Order Total Price" in results.columns:
        results["Order Total Price (MWK)"] = results["Order Total Price"].apply(lambda x: f"{float(x):,.0f}")
    out_cols = [c for c in DISPLAY_FIELDS if c != "Order Total Price"] + ["Order Total Price (MWK)"]
    out = results[out_cols].to_dict("records")
    collected = load_collected()
    order_nos = results["Order No"].astype(str).unique().tolist()
    already = collected[collected["Order No"].astype(str).isin(order_nos)]
    if already.empty:
        status = html.Div("Status: NOT DELIVERED", style={"color": "#FFA500", "fontWeight": "bold"})
    else:
        statuses = already["Status"].unique()
        if "Undelivered" in statuses:
            status = html.Div("Status: UNDELIVERED", style={"color": "#FF4500", "fontWeight": "bold"})
        else:
            status = html.Div("Status: DELIVERED", style={"color": "#28A745", "fontWeight": "bold"})
    return out, status

@app.callback(
    [Output("action-msg", "children", allow_duplicate=True),
     Output("collected-table", "data", allow_duplicate=True)],
    Input("mark-btn", "n_clicks"),
    State("search-input", "value"),
    prevent_initial_call="initial_duplicate"
)
def mark_collected(n_clicks, query):
    if not query:
        return "", load_collected().to_dict("records")
    df = MASTER_DF
    q = str(query).strip()
    mask = df["Order No"].astype(str).str.contains(q, case=False, na=False) | df["Contact"].astype(str).str.contains(q, case=False, na=False)
    results = df[mask].copy()
    if results.empty:
        return "No matching records to mark.", load_collected().to_dict("records")
    collected = load_collected()
    now = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    new_rows = []
    for order in results["Order No"].astype(str).unique():
        if not ((collected["Order No"].astype(str) == str(order)).any()):
            contact = results.loc[results["Order No"].astype(str) == str(order), "Contact"].iloc[0] if "Contact" in results.columns else ""
            new_rows.append({"Order No": str(order), "Contact": str(contact), "MarkedBy": "AGRONOMIST", "Timestamp": now, "Status": "Delivered"})
    if new_rows:
        collected = pd.concat([collected, pd.DataFrame(new_rows)], ignore_index=True)
        save_collected(collected)
        msg = "✅ Marked as DELIVERED."
    else:
        msg = "⚠️ Already marked delivered."
    return msg, collected.to_dict("records")

@app.callback(
    Output("confirm-undeliver", "displayed"),
    Input("undeliver-btn", "n_clicks"),
    prevent_initial_call=True
)
def show_confirm(n):
    return True

@app.callback(
    [Output("action-msg", "children", allow_duplicate=True),
     Output("collected-table", "data", allow_duplicate=True)],
    Input("confirm-undeliver", "submit_n_clicks"),
    State("search-input", "value"),
    prevent_initial_call="initial_duplicate"
)
def confirm_undeliver(submit_n, query):
    if not query:
        return "No order selected.", load_collected().to_dict("records")
    df = load_collected()
    q = str(query).strip()
    mask = df["Order No"].astype(str).str.contains(q, case=False, na=False) | df["Contact"].astype(str).str.contains(q, case=False, na=False)
    if not mask.any():
        return "No delivered record found to mark undelivered.", df.to_dict("records")
    df.loc[mask, "Status"] = "Undelivered"
    save_collected(df)
    return "🔄 Marked as UNDELIVERED.", df.to_dict("records")

# === Sync button callback ===
@app.callback(
    Output("sync-msg", "children"),
    Input("sync-btn", "n_clicks"),
    prevent_initial_call=True
)
def sync_to_email(n):
    if n > 0:
        success = send_csv_to_email()
        if success:
            return "✅ Sync successful — email sent to stephenlongwe78@gmail.com."
        else:
            return "❌ Failed to send email. Check your connection or .env credentials."
    return ""

if __name__ == "__main__":
    app.run_server(mode="inline", debug=True)
