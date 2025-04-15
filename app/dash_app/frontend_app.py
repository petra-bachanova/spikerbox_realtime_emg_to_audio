# frontend.py
import dash
from dash import dcc, html
import dash_daq as daq
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from flask import Flask
from flask_socketio import SocketIO
from plotly.subplots import make_subplots
import plotly.express as px

from app.utils.config import Config

# Setup Flask server with SocketIO
server = Flask(__name__)
socketio = SocketIO(server, cors_allowed_origins="*")
app = dash.Dash(__name__, server=server)

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
# Track the time when calibration mode is activated
calibration_start_time = None
calibration_amplitudes = []  # List to store RMS amplitudes during calibration mode
signal_frequency_magnitude = []

# Define the Dash layout
app.layout = html.Div([
    html.H1("Make your muscles sing!"),
    html.Div([
        html.Button(
            'Stop Streaming',
            id='stream-button',
            style={
                'backgroundColor': '#FF5555',
                'color': 'white',
                'padding': '10px 20px',
                'fontSize': '16px',
                'borderRadius': '5px',
                'margin': '10px 0px'
            }
        ),
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
            )
    ]),
    # html.Div(
    #     [
    #         daq.ToggleSwitch(
    #             id='calibrate-mode',
    #             label='Calibrate mode',
    #             labelPosition='left',
    #             value=False
    #         )
    #     ],
    #     style={
    #         'backgroundColor': '#FF9999',
    #         'color': 'white',
    #         'padding': '10px 20px',
    #         'fontSize': '20px',
    #         'borderRadius': '5px',
    #         'margin': '10px 0px',
    #         'display': 'inline-block',
    #         'textAlign': 'center',
    #         'border': '2px solid black'
    #     }
    # ),
    # html.Div(
    #     id='calibrate-message',
    #     children="Relax your muscles...",
    #     style={
    #         'display': 'none',  # Initially hidden
    #         'backgroundColor': '#FFFF99',
    #         'color': 'black',
    #         'padding': '10px 20px',
    #         'fontSize': '18px',
    #         'borderRadius': '5px',
    #         'margin': '10px 0px',
    #         'textAlign': 'center',
    #         'border': '2px solid black'
    #     }
    # ),
    # html.Div(
    #     id='calibrate-stats',
    #     children="",
    #     style={
    #         'display': 'none',  # Initially hidden
    #         'backgroundColor': '#FFFFCC',
    #         'color': 'black',
    #         'padding': '10px 20px',
    #         'fontSize': '18px',
    #         'borderRadius': '5px',
    #         'margin': '10px 0px',
    #         'textAlign': 'center',
    #         'border': '2px solid black'
    #     }
    # ),
    dcc.Graph(id='frame-plot', animate=False),
    dcc.Graph(id='freq-magnitude-plot', animate=False),
    dcc.Interval(
        id='frame-update',
        interval=1000 * config.update_interval,  # Update graph every x ms
        n_intervals=0
    ),
    # Hidden div to store the stream state
    html.Div(id='stream-state', style={'display': 'none'}, children='active')
])

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
    global signal_points
    global signal_point_times
    global rms_amplitudes
    global rms_amplitude_times
    global max_frame_points

    global signal_frequency_magnitude

    # Only process incoming data if streaming is active
    if streaming_active:
        signal_points.extend(data['data']['frame'])
        signal_point_times.extend(data['data']['frame_time'])
        frame_len = len(data['data']['frame'])

        rms_amplitudes.append(data['data']['rms_amplitude'])
        rms_amplitude_times.append(data['data']['rms_sample_time'])

        signal_frequency_magnitude = data['data']['frequency_magnitude']
        # signal_frequency_magnitude = signal_frequency_magnitude[:3]
        # print("handle_signal_frame_data_update")
        # print(signal_frequency_magnitude)

        # Keep only the latest points
        if len(signal_points) > max_frame_points:
            signal_points = signal_points[frame_len:]
            signal_point_times = signal_point_times[frame_len:]

            first_frame_time = signal_point_times[0]

            # Remove entries in rms_amplitude_times and rms_amplitudes less than first_frame_time
            filtered_indices = [i for i, t in enumerate(rms_amplitude_times) if t >= first_frame_time]
            rms_amplitude_times = [rms_amplitude_times[i] for i in filtered_indices]
            rms_amplitudes = [rms_amplitudes[i] for i in filtered_indices]


@socketio.on('request_streaming_state')
def send_streaming_state():
    socketio.emit('streaming_state', {'active': streaming_active})


# Callback for the button
@app.callback(
    [Input('clear-graphs-button', 'n_clicks')]
)
def clear_graphs_and_data(n_clicks):
    # global streaming_active
    global signal_points
    global signal_point_times
    signal_points = []
    signal_point_times = []


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
        return 'Stop Streaming', {
            'backgroundColor': '#FF5555',
            'color': 'white',
            'padding': '10px 20px',
            'fontSize': '16px',
            'borderRadius': '5px',
            'margin': '10px 0px'
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
            'margin': '10px 0px'
        }, 'inactive'
    else:
        # Switch to active
        streaming_active = True
        socketio.emit('streaming_state', {'active': True})
        return 'Stop Streaming', {
            'backgroundColor': '#FF5555',
            'color': 'white',
            'padding': '10px 20px',
            'fontSize': '16px',
            'borderRadius': '5px',
            'margin': '10px 0px'
        }, 'active'


@app.callback(
    Output('freq-magnitude-plot', 'figure'),
    [Input('frame-update', 'n_intervals')]
)
def update_freq_magnitude_plot(n):
    global signal_frequency_magnitude

    if not signal_frequency_magnitude:
        # If no data is available, return an empty figure
        print("No signal frequency magnitude data available.")
        return go.Figure()

    # print("update_freq_magnitude_plot")
    # print(signal_frequency_magnitude)

    # unzip to two iterators
    freqs, magnitude = zip(*signal_frequency_magnitude)

    # freqs = [10, 20, 30, 40]
    # magnitude = [0.5, 0.8, 0.3, 0.6]

    # print(freqs)

    fig = px.line(
        x=list(freqs),
        y=list(magnitude),
        labels={'x': 'Frequency (Hz)', 'y': 'Magnitude'},
        title="Frequency Spectrum"
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

    # Create a subplot with two rows and one column
    fig = make_subplots(
        rows=2, cols=1,  # Two rows, one column
        shared_xaxes=True,  # Share the x-axis between the two plots
        vertical_spacing=0.1,  # Space between the plots
        subplot_titles=(
            "Raw Data",
            "RMS Amplitudes",
            ),  # Titles for each subplot
    )

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

    # Update layout for the figure
    fig.update_layout(
        title="Raw Data and RMS Amplitudes",
        xaxis=dict(title="Time (s)"),  # Shared x-axis title
        yaxis=dict(title="Raw Data"),  # Y-axis for the first subplot
        yaxis2=dict(title="RMS Amplitudes"),  # Y-axis for the second subplot
        height=600,  # Adjust the height of the figure
        margin=dict(l=50, r=50, t=50, b=50),  # Margins
        legend=dict(x=0, y=1)  # Position the legend
    )

    return fig


if __name__ == '__main__':
    print("Starting frontend server on http://localhost:8501")
    socketio.run(server, debug=False, port=8501)
