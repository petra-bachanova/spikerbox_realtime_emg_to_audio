# frontend.py
from datetime import datetime
import dash
from dash import dcc, html
import dash_daq as daq
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from flask import Flask
from flask_socketio import SocketIO
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np

from app.utils.config import Config

# Setup Flask server with SocketIO
server = Flask(__name__)
socketio = SocketIO(server, cors_allowed_origins="*")
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
    )

config = Config()

# Global variables to store data
signal_points = []
signal_point_times = []
times = []
values = []
rms_amplitudes = []
rms_amplitude_times = []
max_frame_points = int(config.plot_time_span * config.plot_points_per_second)
streaming_active = True  # Flag to control streaming state
# Global variable to store the calibrate mode state
calibrate_mode = False
record_data_mode = config.save_recording
# Track the time when calibration mode is activated
calibration_start_time = None
calibration_amplitudes = []  # List to store RMS amplitudes during calibration mode
signal_frequency_magnitude = {}
freq_data_min_max = []  # min and max frequences in frequency data passed from backend
all_frequencies = []
all_magnitudes = []
save_timestamp = datetime.now()
back_end_is_connected = False
data_available_status = False
max_magnitude = 0

modal_filename_div = html.Div(
    [
        dbc.Label("File name"),
        dbc.Input(id="input-filename", value="atest", placeholder="uuid"),
        dbc.FormFeedback("Input can only contain alphanumerics and underscores", type="invalid"),
    ],
    className="mb-3",
)

@app.callback(
    Output("input-filename", "valid"),
    Output("input-filename", "invalid"),
    Output("save-data-button", "disabled"),
    Input("input-filename", "value"),
)
def validate_file_name_input(value):
    if value is None or "." in value or value == "":
        return False, True, True  # Show invalid feedback and disable save button
    else:
        return True, False, False   # Show valid feedback

hr_component = html.Hr(
    style={
        'flexGrow': 1,
        'borderWidth': "1px",
        'borderColor': "#808080",
        'opacity': "unset",
        'marginLeft': "10px"
    })

participant_age_div = html.Div(
    [
        dbc.Label("Participant age"),
        dbc.Select(
            id="age-select",
            options=[
                {"label": "N/A", "value": "N/A"},
                {"label": "0-10", "value": "0-10"},
                {"label": "11-20", "value": "11-20"},
                {"label": "21-30", "value": "21-30"},
                {"label": "31-40", "value": "31-40"},
                {"label": "41-50", "value": "41-50"},
                {"label": "50+", "value": "50+"},
            ],
            placeholder="Select age range",
        ),
    ]
)

# Modify the Dash layout - Add a container with margins
app.layout = html.Div([
    # Main container with margins
    dbc.Container([
        html.H1("Make your muscles sing!", className="mt-4"),
        
        # Create a row with three columns for the controls
        dbc.Row([
            # Section 1: Streaming Controls
            dbc.Col([
                # Container for heading and HR that will be as wide as buttons below
                html.Div([
                    # Flexbox container for heading and HR
                    html.Div([
                        html.H5("Streaming controls", style={"margin": 0, "whiteSpace": "nowrap"}),
                        html.Div(hr_component, style={"flexGrow": 1, "marginLeft": "10px"}),
                    ], style={"display": "flex", "alignItems": "center", "width": "100%"}),
                    
                    # Button row
                    dbc.Row([
                        dbc.Col(
                            html.Button(
                                'Pause stream',
                                id='stream-button',
                                style={
                                    'backgroundColor': '#FF5555',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'fontSize': '16px',
                                    'borderRadius': '5px',
                                    'margin': '10px 0px',
                                    'width': '160px'
                                }
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            html.Button(
                                'Clear graphs',
                                id='clear-graphs-button',
                                style={
                                    'backgroundColor': '#FF5555',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'fontSize': '16px',
                                    'borderRadius': '5px',
                                    'margin': '10px 0px'
                                }
                            ),
                            width="auto",
                        )
                    ],
                        justify="start",
                        className="g-2"),
                ], style={"display": "inline-block"}),  # This div constrains width to content
            ], width=4),

            # Section 2: Data Recording Controls
            dbc.Col([

                html.Div([
                    # Flexbox container for heading and HR
                    html.Div([
                        html.H5("Data recording", style={"margin": 0, "whiteSpace": "nowrap"}),
                        html.Div(hr_component, style={"flexGrow": 1, "marginLeft": "10px"}),
                    ], style={"display": "flex", "alignItems": "center", "width": "100%"}),
                
                    # html.Div([
                    #     html.H5("Data recording", style={"margin": 0, "paddingRight": "10px"}),
                    #     hr_component,
                    # ], style={"display": "flex", "alignItems": "center", "width": "100%"}
                    # ),

                    # Button row
                    dbc.Row([
                        dbc.Col(
                            html.Button(
                                "Start recording",
                                id='start-record-data-button',
                                disabled=False,
                                style={
                                    'backgroundColor': '#FF5555',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'fontSize': '16px',
                                    'borderRadius': '5px',
                                    'margin': '10px 0'
                                }
                            ),
                            width="auto",  # Adjust column width to fit the button
                        ),
                        dbc.Col(
                            html.Button(
                                "Stop recording",
                                id='stop-record-data-button',
                                disabled=True,
                                style={
                                    'backgroundColor': '#ffe0e0',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'fontSize': '16px',
                                    'borderRadius': '5px',
                                    'margin': '10px 0'
                                }
                            ),
                            width="auto"  # Adjust column width to fit the button
                        )
                    ],
                        justify="start",  # Align left
                        className="g-2"),  # Add margin between rows
                    ], style={"display": "inline-block"}),  # This div constrains width to content
                ], width=4),

            # Section 3: Status Display
            dbc.Col([
                html.Div([
                    html.H5("Status", style={"margin": 0, "paddingRight": "10px"}),
                    hr_component,
                ], style={"display": "flex", "alignItems": "center", "width": "100%"}
                ),

                dbc.Card(
                    dbc.CardBody(
                        id="status-card-body",
                        children="⚠️ backend disconnected",
                        # className="d-flex align-items-center",  # Replaces flexbox styling
                        className="d-flex align-items-center py-0 px-3", # Zero vertical padding, normal horizontal padding
                        style={"height": "100%"}, # Ensure CardBody fills the entire Card height
                        ),
                    id="status-card",
                    className="mb-3 mt-2",  # Combines margin classes
                    color="danger",  # Sets border color (red, similar to your #FF5555)
                    outline=True,    # Makes it an outline card with transparent background
                    style={"height": "50px"}
                ),
            ], width=4)
        ], className="mb-4"),
        ],
    # Set a maximum width and add margins
    fluid=True,  # Use fluid to allow responsive width
    style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '0 50px'}),

    dbc.Container([
        # Graphs section
        html.Div(
            [
                dcc.Graph(
                    id='frame-plot',
                    animate=False,
                    style={'flex': '1', 'margin-right': '10px'}
                    ),
                dcc.Graph(
                    id='freq-magnitude-plot',
                    animate=False,
                    style={'flex': '1', 'align-self': 'center'}
                    )
            ],
            style={
                'display': 'flex',
                'flex-direction': 'row',
                'align-items': 'center'
                }),
        ],
        # Set a maximum width and add margins
        fluid=True,  # Use fluid to allow responsive width
        style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '0 20px'}),

    # Components outside container
    dcc.Interval(
        id='frame-update',
        interval=1000 * config.update_interval,
        n_intervals=0,
        disabled=False
    ),
    html.Div(id='stream-state', style={'display': 'none'}, children='active'),
    dbc.Modal(
        [
            dbc.ModalHeader("Save recording"),
            dbc.ModalBody(
                [
                    dbc.Form(
                        [
                            modal_filename_div,
                            participant_age_div,
                        ]
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Save", id="save-data-button", n_clicks=0, disabled=False),
                    dbc.Button("Cancel", id="cancel-modal", className="ms-2", n_clicks=0),
                ],
                className="d-flex justify-content-end",
            ),
        ],
        id="stop-recording-modal",
        is_open=False,
    ),
    dcc.Interval(
        id='backend-connection-checker',
        interval=1000,
        n_intervals=0
    ),
    dcc.Interval(
        id='data-available-checker',
        interval=500,
        n_intervals=0
    ),
    dcc.Store(
        id='backend-connection-status',
        data=back_end_is_connected
        ),
    dcc.Store(
        id='data-available-status',
        data=False
        ),
])

@app.callback(
    Output('data-available-status', 'data'),
    Input('data-available-checker', 'n_intervals')
)
def update_data_available_status(n):
    global data_available_status
    # Return the current value of data_available_status
    return data_available_status

@app.callback(
    Output('backend-connection-status', 'data'),
    Input('backend-connection-checker', 'n_intervals')
)
def update_backend_connection_status(n):
    global back_end_is_connected
    # Return the current value of back_end_is_connected
    return back_end_is_connected

@app.callback(
    [Output("status-card-body", "children"),
     Output("status-card", "color")],
    [Input("backend-connection-status", "data"),
     Input("data-available-status", "data")]
)
def update_status_card(connected, data_available):
    # Handle None values that might occur during initialization
    if connected is None:
        connected = False
    if data_available is None:
        data_available = False

    global config

    if not connected:
        color = "danger"
        text = "⚠️ backend disconnected"
    elif not data_available:
        color = "warning"
        if config.use_live_data:
            text = "Backend connected; no data from Spikerbox"
        else:
            text = "Backend connected; initializing data, or reached end of file"
    else:
        color = "success"
        text = "💪 we're singing"  # or whatever status message you intended

    return text, color

@app.callback(
    Output('frame-update', 'disabled'),
    [Input('stop-recording-modal', 'is_open')]
)
def toggle_interval(modal_is_open):
    # Disable interval updates when modal is open
    return modal_is_open

@app.callback(
    [Output("stop-recording-modal", "is_open"),
     Output("input-filename", "value")],
    [Input("stop-record-data-button", "n_clicks"),
     Input("save-data-button", "n_clicks"),
     Input("cancel-modal", "n_clicks")],
    [State("input-filename", "value"),
     State("age-select", "value"),
     State("stop-recording-modal", "is_open"),]
)
def handle_modal(stop_clicks, save_clicks, cancel_clicks, file_name, age_range, is_open):
    ctx = dash.callback_context
    global save_timestamp
    
    if not ctx.triggered:
        return is_open, ""  # No input triggered, return current modal state
    
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if triggered_id == "stop-record-data-button":
        # Open the modal when stop recording is clicked
        # update timestamp
        save_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return True, save_timestamp
    
    elif triggered_id == "cancel-modal":
        # Close the modal when cancel is clicked
        return False, ""
    
    elif triggered_id == "save-data-button" and save_clicks:
        # Process the data when save is clicked
        if not age_range or age_range == "":
            age_range = "N/A"
        if file_name and age_range:
            save_metadata = {
                "file_name": file_name,
                "age_range": age_range
            }
            socketio.emit('complete_save_data', save_metadata)
        
        # Close the modal after saving
        return False, ""
    
    # Default: return current modal state
    return is_open, ""

@app.callback(
    [Output('calibrate-message', 'style'),
     Output('calibrate-stats', 'style'),
     Output('calibrate-stats', 'children')],
    [Input('calibrate-mode', 'value')],
    [State('calibrate-stats', 'children')]
)
def toggle_calibrate_message_and_stats(calibrate_mode, current_stats):
    global calibration_amplitudes, rms_amplitudes
    global calibration_min, calibration_max

    if calibrate_mode:
        # Calibration mode is active
        if not calibration_amplitudes:
            # Clear the list when calibration mode is first turned on
            calibration_amplitudes = []

        # Append the latest RMS amplitude values to the calibration list
        calibration_amplitudes.extend(rms_amplitudes)

        # Show the "Relax your muscles" message and hide stats
        return (
            {
                'display': 'block',
                'backgroundColor': '#FFFF99',
                'color': 'black',
                'padding': '10px 20px',
                'fontSize': '18px',
                'borderRadius': '5px',
                'margin': '10px 0px',
                'textAlign': 'center',
                'border': '2px solid black'
            },
            {'display': 'none'},  # Hide stats while calibration is active
            ""
        )
    else:
        # Calibration mode is turned off
        if calibration_amplitudes:
            # Calculate min and max from the calibration list
            calibration_min = min(calibration_amplitudes)
            calibration_max = max(calibration_amplitudes)
            stats_message = f"Min RMS Amplitude: {calibration_min:.2f}, Max RMS Amplitude: {calibration_max:.2f}"
        else:
            stats_message = "No data available."

        # Clear the calibration list after use
        calibration_amplitudes = []

        # Hide the "Relax your muscles" message and show stats
        return (
            {'display': 'none'},  # Hide the message
            {
                'display': 'block',
                'backgroundColor': '#FFFFCC',
                'color': 'black',
                'padding': '10px 20px',
                'fontSize': '18px',
                'borderRadius': '5px',
                'margin': '10px 0px',
                'textAlign': 'center',
                'border': '2px solid black'
            },
            stats_message
        )

# Callback to update the global variable based on the ToggleSwitch position
@app.callback(
    Output('calibrate-mode', 'value'),
    [Input('calibrate-mode', 'value')]
)
def update_calibrate_mode(toggle_value):
    global calibrate_mode
    calibrate_mode = toggle_value  # Update the global variable
    return toggle_value

# WebSocket event handler
# TODO - is this used?
@socketio.on('connect')
def handle_connect():
    print('Client connected to server')
    # Tell the client the current streaming state
    socketio.emit('streaming_state', {'active': streaming_active})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from server')


@socketio.on('signal_frame_update')
def handle_signal_frame_data_update(data):
    global config

    global signal_points
    global signal_point_times
    global rms_amplitudes
    global rms_amplitude_times
    global max_frame_points

    global signal_frequency_magnitude
    global freq_data_min_max
    global all_frequencies, all_magnitudes

    # Only process incoming data if streaming is active
    if streaming_active:
        signal_points.extend(data['data']['frame'])
        signal_point_times.extend(data['data']['frame_time'])
        frame_len = len(data['data']['frame'])

        rms_amplitudes.append(data['data']['rms_amplitude'])
        rms_amplitude_times.append(data['data']['rms_sample_time'])

        # print("rms_amplitude_times")
        # print(len(rms_amplitude_times))
        # print(config.update_interval)
        # print(config.plot_points_per_second)
        # print(config.plot_time_span)

        signal_frequency_magnitude = data['data']['frequency_magnitude']
        freq_data_min_max = data['data']['frequency_magnitude_freq_min_max']
        # signal_frequency_magnitude = data['data']['frequency_magnitude_2']
        # signal_frequency_magnitude = signal_frequency_magnitude[:3]
        # print("handle_signal_frame_data_update")
        # print(signal_frequency_magnitude)

        fs = np.linspace(freq_data_min_max[0], freq_data_min_max[1], config.freq_plot_bins)
        all_frequencies.append(list(fs))
        # all_frequencies.append(signal_frequency_magnitude["x"])
        all_magnitudes.append(signal_frequency_magnitude["y"])
        # all_magnitudes.append(signal_frequency_magnitude)

        # Keep only the latest points
        if len(signal_points) > max_frame_points:
            signal_points = signal_points[frame_len:]
            signal_point_times = signal_point_times[frame_len:]

            # first_frame_time is dynamic,
            # and represents the first time shown in the signal plot
            first_frame_time = signal_point_times[0]

            # Remove entries in rms_amplitude_times and rms_amplitudes less than first_frame_time
            filtered_indices = [i for i, t in enumerate(rms_amplitude_times) if t >= first_frame_time]
            rms_amplitude_times = [rms_amplitude_times[i] for i in filtered_indices]
            rms_amplitudes = [rms_amplitudes[i] for i in filtered_indices]

            all_frequencies = [all_frequencies[i] for i in filtered_indices]
            all_magnitudes = [all_magnitudes[i] for i in filtered_indices]

@socketio.on('data_available_message')
def update_data_available_status(data):
    global data_available_status
    data_available_status_str = data.get('data', "False")
    if data_available_status_str == "True":
        data_available_status = True
    else:
        data_available_status = False

@socketio.on('backend_connected')
def update_connection_status(data):
    global back_end_is_connected
    back_end_is_connected_str = data.get('status', "False")
    if back_end_is_connected_str == "True":
        back_end_is_connected = True
    else:
        back_end_is_connected = False


@socketio.on('request_streaming_state')
def send_streaming_state():
    socketio.emit('streaming_state', {'active': streaming_active})


@app.callback(
    Output('start-record-data-button', 'disabled'),
    Output('start-record-data-button', 'style'),
    Output('stop-record-data-button', 'disabled'),
    Output('stop-record-data-button', 'style'),
    Input('start-record-data-button', 'n_clicks'),
    Input('stop-record-data-button', 'n_clicks')
)
def handle_recording_buttons(start_clicks, stop_clicks):
    print("handle_recording_buttons triggered")
    print(dash.callback_context.triggered)
    # Determine which button was clicked
    ctx = dash.callback_context

    if not ctx.triggered:
        # Page load: return default styles and states
        return (
            False,  # start-record-data-button is enabled
            {
                'backgroundColor': '#FF5555',
                'color': 'white',
                'padding': '10px 20px',
                'fontSize': '16px',
                'borderRadius': '5px',
                'margin': '10px 0px'
            },
            True,  # stop-record-data-button is disabled
            {
                'backgroundColor': '#ffe0e0',
                'color': 'white',
                'padding': '10px 20px',
                'fontSize': '16px',
                'borderRadius': '5px',
                'margin': '10px 0px'
            }
        )

    global record_data_mode

    # Check which button was clicked
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_id == 'start-record-data-button':
        # Start recording button clicked
        print("handle_start_recording_button")
        record_data_mode = True
        socketio.emit('save_data', {'active': True})
        return (
            True,  # Disable start button
            {
                'backgroundColor': '#ffe0e0',
                'color': 'white',
                'padding': '10px 20px',
                'fontSize': '16px',
                'borderRadius': '5px',
                'margin': '10px 0px'
            },
            False,  # Enable stop button
            {
                'backgroundColor': '#FF5555',
                'color': 'white',
                'padding': '10px 20px',
                'fontSize': '16px',
                'borderRadius': '5px',
                'margin': '10px 0px'
            }
        )
    elif triggered_id == 'stop-record-data-button':
        # Stop recording button clicked
        print("handle_stop_recording_button")
        record_data_mode = False
        socketio.emit('save_data', {'active': False})
        return (
            False,  # Enable start button
            {
                'backgroundColor': '#FF5555',
                'color': 'white',
                'padding': '10px 20px',
                'fontSize': '16px',
                'borderRadius': '5px',
                'margin': '10px 0px'
            },
            True,  # Disable stop button
            {
                'backgroundColor': '#ffe0e0',
                'color': 'white',
                'padding': '10px 20px',
                'fontSize': '16px',
                'borderRadius': '5px',
                'margin': '10px 0px'
            }
        )


# Callback for the button
@app.callback(
    [Input('clear-graphs-button', 'n_clicks')]
)
def clear_graphs_and_data(n_clicks):
    # global streaming_active
    global signal_points
    global signal_point_times
    global rms_amplitudes
    global rms_amplitude_times
    global all_frequencies, all_magnitudes
    global signal_frequency_magnitude

    signal_points = []
    signal_point_times = []
    rms_amplitudes = []
    rms_amplitude_times = []
    all_frequencies = []
    all_magnitudes = []
    signal_frequency_magnitude = {}


# Callback for the button
@app.callback(
    [Output('stream-button', 'children'),
     Output('stream-button', 'style'),
     Output('stream-state', 'children')],
    [Input('stream-button', 'n_clicks')],
    [State('stream-state', 'children')]
)
def toggle_stream(n_clicks, stream_state):
    global streaming_active
    
    if n_clicks is None:
        # Initial state
        return 'Pause stream', {
            'backgroundColor': '#FF5555',
            'color': 'white',
            'padding': '10px 20px',
            'fontSize': '16px',
            'borderRadius': '5px',
            'margin': '10px 0px',
            'width': '160px'
        }, 'active'
    
    if stream_state == 'active':
        # Switch to inactive
        streaming_active = False
        socketio.emit('streaming_state', {'active': False})
        return 'Start Streaming', {
            'backgroundColor': '#55AA55',
            'color': 'white',
            'padding': '10px 20px',
            'fontSize': '16px',
            'borderRadius': '5px',
            'margin': '10px 0px',
            'width': '160px'
        }, 'inactive'
    else:
        # Switch to active
        streaming_active = True
        socketio.emit('streaming_state', {'active': True})
        return 'Pause stream', {
            'backgroundColor': '#FF5555',
            'color': 'white',
            'padding': '10px 20px',
            'fontSize': '16px',
            'borderRadius': '5px',
            'margin': '10px 0px',
            'width': '160px'
        }, 'active'
    

def get_max_magnitude():
    global all_magnitudes
    global max_magnitude
    max_magnitude = max([max(i) for i in all_magnitudes])


@app.callback(
    Output('freq-magnitude-plot', 'figure'),
    [Input('frame-update', 'n_intervals')]
)
def update_freq_magnitude_plot(n):
    global config
    global signal_frequency_magnitude
    global freq_data_min_max
    global max_magnitude

    if not signal_frequency_magnitude:
        # If no data is available, return an empty figure
        return go.Figure()

    freqs = np.linspace(freq_data_min_max[0], freq_data_min_max[1], config.freq_plot_bins)
    magnitude = signal_frequency_magnitude["y"]

    fig = px.line(
        x=list(freqs),
        y=list(magnitude),
        labels={'x': 'Frequency (Hz)', 'y': 'Magnitude'},
        title="Live frequency spectrum",
        range_y=[0, max_magnitude],
        )

    # Fix the margin to prevent title clipping and adjust height
    fig.update_layout(
        margin=dict(l=50, r=50, t=50, b=50),  # Increased top margin from 20 to 50
        height=400,                           # Match height of left graph
        title_x=0.5,                          # Center the title
        title_y=0.95                          # Position title slightly lower from the top
    )

    return fig


@app.callback(
    Output('frame-plot', 'figure'),
    [Input('frame-update', 'n_intervals')]
)
def update_frame_plot(n):
    global signal_points
    global signal_point_times
    global rms_amplitudes
    global rms_amplitude_times
    global all_frequencies, all_magnitudes
    global max_magnitude

    # Create a subplot with two rows and one column
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,  # Space between the plots
        subplot_titles=(
            "Raw Data",
            "RMS Amplitudes",
            "Spectrogram",
            ),  # Titles for each subplot
    )

    if not signal_point_times:
        return fig
    
    get_max_magnitude()

    # Add the "raw data" trace to the first subplot
    fig.add_trace(
        go.Scatter(
            x=signal_point_times,
            y=signal_points,
            name='Raw Data',
            mode='lines'
        ),
        row=1, col=1  # Specify the first row
    )

    # Add the "rms_amplitudes" trace to the second subplot
    fig.add_trace(
        go.Scatter(
            x=rms_amplitude_times,
            y=rms_amplitudes,
            name='RMS Amplitudes',
            mode='lines'
        ),
        row=2, col=1  # Specify the second row
    )

    fig.add_trace(
        go.Heatmap(
            z=np.array(all_magnitudes).T,  # Shape: freq x time,
            x=rms_amplitude_times,
            y=all_frequencies[-1],
            colorscale='Viridis',
            zmin=0,
            zmax=max_magnitude,
            coloraxis="coloraxis1"  # Assign to a specific color axis
        ),
        row=3, col=1
    )

    # Update layout for the figure
    fig.update_layout(
        title="Time series plots",
        xaxis3=dict(title="Time (s)"),  # Shared x-axis title
        yaxis=dict(title="Raw Data"),  # Y-axis for the first subplot
        yaxis2=dict(title="RMS Amplitudes"),  # Y-axis for the second subplot
        yaxis3=dict(title="Frequency (Hz)", showgrid=False, zeroline=False),  # Y-axis for the third subplot
        height=600,  # Adjust the height of the figure
        margin=dict(l=50, r=50, t=50, b=50),  # Margins
        showlegend=False,  # Show legend
        # legend=dict(x=0, y=1),  # Position the legend
        coloraxis_colorbar=dict(
            title="Magnitude",  # Title for the color scale
            x=1,  # Position the color scale to the right of the third subplot
            y=0.15,  # Align it vertically with the third subplot
            len=0.3  # Adjust the length of the color scale
        )
    )

    return fig


if __name__ == '__main__':
    print("Starting frontend server on http://localhost:8501")
    socketio.run(server, debug=False, port=8501)
