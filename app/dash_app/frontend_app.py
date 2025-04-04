# frontend.py
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from flask import Flask
from flask_socketio import SocketIO
import time

# Setup Flask server with SocketIO
server = Flask(__name__)
socketio = SocketIO(server, cors_allowed_origins="*")
app = dash.Dash(__name__, server=server)

# Global variables to store data
times = []
values = []
max_points = 100  # Maximum number of points to display
streaming_active = True  # Flag to control streaming state

# Define the Dash layout
app.layout = html.Div([
    html.H1("Real-time Data Visualization"),
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
    ]),
    dcc.Graph(id='live-graph', animate=False),
    dcc.Interval(
        id='graph-update',
        interval=200,  # Update graph every x ms
        n_intervals=0
    ),
    # Hidden div to store the stream state
    html.Div(id='stream-state', style={'display': 'none'}, children='active')
])

# WebSocket event handler
@socketio.on('connect')
def handle_connect():
    print('Client connected to server')
    # Tell the client the current streaming state
    socketio.emit('streaming_state', {'active': streaming_active})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from server')

@socketio.on('data_update')
def handle_data_update(data):
    global times, values, streaming_active

    print("handle_data_update")
    print(streaming_active)
    
    # Only process incoming data if streaming is active
    if streaming_active:
        times.append(data['time'])
        values.append(data['value'])

        print(times[-1])
        
        # Keep only the latest points
        if len(times) > max_points:
            times.pop(0)
            values.pop(0)

@socketio.on('request_streaming_state')
def send_streaming_state():
    socketio.emit('streaming_state', {'active': streaming_active})

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

# Dash callback to update graph
@app.callback(
    Output('live-graph', 'figure'),
    [Input('graph-update', 'n_intervals')]
)
def update_graph(n):
    global times, values
    
    fig = go.Figure(
        data=[go.Scatter(
            x=times,
            y=values,
            name='Sensor Data',
            mode='lines+markers'
        )]
    )
    
    # Dynamic range for x and y axes
    x_range = [min(times) if times else 0, max(times) if times else 1]
    y_range = [min(values) if values else 0, max(values) if values else 1]
    
    # Add a small buffer to y-axis range for better visualization
    y_buffer = (y_range[1] - y_range[0]) * 0.1 if y_range[1] != y_range[0] else 0.1
    
    fig.update_layout(
        title='Real-time Data Stream',
        xaxis=dict(range=x_range, title='Time (s)'),
        yaxis=dict(
            range=[y_range[0] - y_buffer, y_range[1] + y_buffer], 
            title='Value'
        ),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

if __name__ == '__main__':
    print("Starting frontend server on http://localhost:8501")
    socketio.run(server, debug=True, port=8501)