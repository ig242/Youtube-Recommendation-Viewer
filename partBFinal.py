import dash
from dash import html, dcc, Input, Output, State, callback_context, no_update
import plotly.graph_objects as go
from serpapi import GoogleSearch
import networkx as nx
import requests

app = dash.Dash(__name__)

def fetch_youtube_category(video_id):
    api_key = "" #Enter here YouTube API key
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    category_id = data['items'][0]['snippet']['categoryId'] if data['items'] else 'Unknown'
    return category_id
def get_category_name(category_id):
    category_map = {
        '1': 'Film & Animation',
        '2': 'Autos & Vehicles',
        '10': 'Music',
        '15': 'Pets & Animals',
        '17': 'Sports',
        '18': 'Short Movies',
        '19': 'Travel & Events',
        '20': 'Gaming',
        '21': 'Video Blogging',
        '22': 'People & Blogs',
        '23': 'Comedy',
        '24': 'Entertainment',
        '25': 'News & Politics',
        '26': 'Howto & Style',
        '27': 'Education',
        '28': 'Science & Technology',
        '29': 'Nonprofits & Activism',
        '30': 'Movies',
        '31': 'Anime/Animation',
        '32': 'Action/Adventure',
        '33': 'Classics',
        '34': 'Comedy',
        '35': 'Documentary',
        '36': 'Drama',
        '37': 'Family',
        '38': 'Foreign',
        '39': 'Horror',
        '40': 'Sci-Fi/Fantasy',
        '41': 'Thriller',
        '42': 'Shorts',
        '43': 'Shows',
        '44': 'Trailers'
    }
    return category_map.get(category_id, 'Unknown')

def fetch_video_details(video_id):
    api_key = "" #Enter here SerpApi key
    try:
        params = {
            "engine": "youtube_video",
            "v": video_id,
            "api_key": api_key
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        category_id = fetch_youtube_category(video_id)
        category_name = get_category_name(category_id)
        results['category'] = category_name
    except Exception as e:
        print(f"Error fetching video details for video ID {video_id}: {e}")
        results = {'title': video_id, 'category': 'Unknown'}
    return results


def create_graph(initial_video_ids):
    G = nx.DiGraph()
    initial_node = "User Starting Point"
    G.add_node(initial_node, title=initial_node, color='red', size=20)

    for video_id in initial_video_ids:
        video_details = fetch_video_details(video_id)
        video_title = video_details.get('title', f"Missing Title for {video_id}")
        video_category = video_details.get('category', 'Unknown')

        G.add_node(video_title, title=video_title, category=video_category, video_id=video_id, color='blue', size=15)
        G.add_edge(initial_node, video_title)

        related_videos = video_details.get('related_videos', [])
        for video in related_videos[:3]:
            related_video_title = video.get('title', f"Missing Title for related video of {video_id}")
            related_video_category = video_details.get('category', 'Unknown')

            G.add_node(related_video_title, title=related_video_title, category=related_video_category,
                       video_id=video.get('video_id', 'Unknown'), color='orange', size=10)
            G.add_edge(video_title, related_video_title)

    pos = nx.planar_layout(G)
    for node, p in pos.items():
        G.nodes[node]['pos'] = p

    return G


def create_plotly_graph(video_ids):
    G = create_graph(video_ids)
    x_edges, y_edges = [], []

    for edge in G.edges():
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        x_edges.extend([x0, x1, None])
        y_edges.extend([y0, y1, None])

    edge_trace = go.Scatter(x=x_edges, y=y_edges, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')
    node_trace = go.Scatter(
        x=[G.nodes[node]['pos'][0] for node in G.nodes()],
        y=[G.nodes[node]['pos'][1] for node in G.nodes()],
        text=[f"{G.nodes[node]['title']} (Category: {G.nodes[node].get('category', 'Unknown')})" for node in G.nodes()],
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=False,
            colorscale='YlGnBu',
            size=[G.nodes[node]['size'] for node in G.nodes()],
            color=[G.nodes[node]['color'] for node in G.nodes()],
            line_width=2),
        customdata=[node for node in G.nodes()]
    )

    fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    ))
    return fig, G

app.layout = html.Div([
    dcc.Textarea(id='video-id-input', placeholder='Enter Video IDs, comma-separated', style={'width': '100%', 'height': 100}),
    html.Button('Submit', id='submit-val', n_clicks=0),
    dcc.Graph(id='video-graph'),
    dcc.Store(id='graph-store'),
    html.Div(id='info-div')
])

@app.callback(
    [Output('video-graph', 'figure'), Output('graph-store', 'data'), Output('info-div', 'children')],
    [Input('submit-val', 'n_clicks'), Input('video-graph', 'clickData')],
    [State('video-id-input', 'value'), State('graph-store', 'data')]
)
def update_output(n_clicks, clickData, video_ids, graph_data):
    ctx = callback_context

    if not ctx.triggered:
        return go.Figure(), {}, "Click on a video node to see details."

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger_id == 'submit-val' and n_clicks > 0 and video_ids:
        video_ids = [vid.strip() for vid in video_ids.split(',')]
        fig, G = create_plotly_graph(video_ids)
        return fig, {node: data for node, data in G.nodes(data=True)}, "Click on a video node to see details."
    elif trigger_id == 'video-graph' and clickData:
        node_id = clickData['points'][0]['customdata']
        if graph_data:
            node_info = graph_data.get(node_id, {})
            video_id = node_info.get('video_id', 'No video ID available')
            info_html = html.Div([
                html.H4("Video Information"),
                html.P(f"Title: {node_info.get('title', 'No title available')}"),
                html.P(f"Category: {node_info.get('category', 'No category available')}"),
                html.P(f"Video ID: {video_id}")
            ])
            return no_update, no_update, info_html

    return no_update, no_update, "Click on a video node to see details."

if __name__ == '__main__':
    app.run_server(debug=True)