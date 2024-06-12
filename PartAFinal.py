import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objects as go
from serpapi import GoogleSearch
import networkx as nx
import json
import requests

app = dash.Dash(__name__)


def fetch_user_videos(user):
    path = '' #Enter here path to JSON file with users
    with open(path, 'r') as file:
        user_videos = json.load(file)
    return user_videos.get(user, {})


def fetch_youtube_category(video_id):
    api_key = '' #Enter here YouTube API key
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
    api_key = "" #Enter here SerpAPI key
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


def calculate_layout_positions(G, main_path, side_branch_spacing=1.0, main_spacing=2.0):
    pos = {}
    current_x = 0.0

    for i, node in enumerate(main_path):
        pos[node] = (current_x, 0)
        current_x += main_spacing
        side_branches = [n for n in G.neighbors(node) if n not in main_path]
        side_y = side_branch_spacing
        for side_node in side_branches:
            pos[side_node] = (pos[node][0], side_y)
            side_y += side_branch_spacing
    return pos


def create_graph(video_data):
    G = nx.DiGraph()
    initial_node = "Start Point"
    G.add_node(initial_node, title=initial_node, color='red', size=20)

    for video_id, suggestions in video_data.items():
        video_details = fetch_video_details(video_id)
        if 'title' in video_details:
            video_title = video_details['title']
            video_category = video_details.get('category', 'Unknown')
            G.add_node(video_title, title=video_title, category=video_category, color='green', size=15)
            G.add_edge(initial_node, video_title)
            for suggested_id in suggestions:
                suggested_details = fetch_video_details(suggested_id)
                if 'title' in suggested_details:
                    suggested_title = suggested_details['title']
                    suggested_category = suggested_details.get('category', 'Unknown')
                    G.add_node(suggested_title, title=suggested_title, category=suggested_category, color='green',
                               size=15)
                    G.add_edge(video_title, suggested_title)
        else:
            print(f"Title not found for Video ID {video_id}")

    return G


def create_plotly_graph(video_data):
    G = nx.DiGraph()
    initial_node = "Start Point"
    G.add_node(initial_node, title=initial_node, category="Initial Category", color='red', size=20)

    current_node = initial_node

    for video_id, suggestions in video_data.items():
        if not suggestions:
            continue
        main_video_details = fetch_video_details(video_id)
        main_video_title = main_video_details.get('title', video_id)
        main_video_category = main_video_details.get('category', 'Unknown')
        G.add_node(video_id, title=main_video_title, category=main_video_category, color='blue', size=15)
        G.add_edge(current_node, video_id)
        current_node = video_id
        for index, suggested_id in enumerate(suggestions):
            suggested_details = fetch_video_details(suggested_id)
            suggested_title = suggested_details.get('title', suggested_id)
            suggested_category = suggested_details.get('category', 'Unknown')
            G.add_node(suggested_id, title=suggested_title, category=suggested_category,
                       color='orange' if index == 0 else 'orange', size=15)
            G.add_edge(video_id, suggested_id)
    main_path = [initial_node] + list(video_data.keys())
    pos = calculate_layout_positions(G, main_path)
    fig = nx_to_plotly_fig(G, pos)
    return fig, G


def nx_to_plotly_fig(G, pos):
    edge_trace = go.Scatter(
        x=[],
        y=[],
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)
    node_trace = go.Scatter(
        x=[],
        y=[],
        text=[],
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=False,
            colorscale='YlGnBu',
            size=[G.nodes[node]['size'] for node in G.nodes()],
            color=[G.nodes[node]['color'] for node in G.nodes()],
            line_width=2))
    for node in G.nodes():
        x, y = pos[node]
        node_trace['x'] += (x,)
        node_trace['y'] += (y,)
        node_title = G.nodes[node]['title']
        node_category = G.nodes[node].get('category', 'Unknown category')
        node_trace['text'] += (f"{node_title} (Category: {node_category})",)
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin={'b': 40, 'l': 40, 'r': 40, 't': 40},
                        xaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
                        yaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False}))
    return fig


app.layout = html.Div([
    html.Div([
        dcc.Dropdown(
            id='user1-dropdown',
            options=[{'label': user, 'value': user} for user in
                     ['User 1 | Category: Entertainment | Age 18+ | Gender Male',
                      'User 2 | Category: Gaming | Age 18- | Gender Male',
                      'User 3 | Category: Entertainment | Age 18+ | Gender Male',
                      'User 4 | Category: News | Age 18+ | Gender Female',
                      'User 5 | Category: Education | Age 18- | Gender Male',
                      'User 6 | Category: Gaming | Age 18+ | Gender Female',
                      'User 7 | Category: Entertainment | Age 18- | Gender Male',
                      'User 8 | Category: News | Age 18+ | Gender Female',
                      'User 9 | Category: Education | Age 18+ | Gender Male',
                      'User 10 | Category: Gaming | Age 18- | Gender Female']],
            placeholder='Select User 1',
            style={'width': '90%', 'display': 'inline-block'}
        ),
        dcc.Dropdown(
            id='user2-dropdown',
            options=[{'label': user, 'value': user} for user in
                     ['User 1 | Category: Entertainment | Age 18+ | Gender Male',
                      'User 2 | Category: Gaming | Age 18- | Gender Male',
                      'User 3 | Category: Entertainment | Age 18+ | Gender Male',
                      'User 4 | Category: News | Age 18+ | Gender Female',
                      'User 5 | Category: Education | Age 18- | Gender Male',
                      'User 6 | Category: Gaming | Age 18+ | Gender Female',
                      'User 7 | Category: Entertainment | Age 18- | Gender Male',
                      'User 8 | Category: News | Age 18+ | Gender Female',
                      'User 9 | Category: Education | Age 18+ | Gender Male',
                      'User 10 | Category: Gaming | Age 18- | Gender Female']],
            placeholder='Select User 2',
            style={'width': '90%', 'display': 'inline-block'}
        ),
        html.Button('Submit', id='submit-val', n_clicks=0)
    ]),
    html.Div([
        dcc.Graph(id='video-graph1'),
        dcc.Graph(id='video-graph2')
    ], style={'display': 'flex'})
])


@app.callback(
    [Output('video-graph1', 'figure'), Output('video-graph2', 'figure')],
    [Input('submit-val', 'n_clicks')],
    [State('user1-dropdown', 'value'), State('user2-dropdown', 'value')]
)
def update_output(n_clicks, user1, user2):
    if not n_clicks:
        return go.Figure(), go.Figure()

    fig1, fig2 = go.Figure(), go.Figure()
    if user1:
        video_data1 = fetch_user_videos(user1)
        fig1, _ = create_plotly_graph(video_data1)
    if user2:
        video_data2 = fetch_user_videos(user2)
        fig2, _ = create_plotly_graph(video_data2)

    return fig1, fig2


if __name__ == '__main__':
    app.run_server(debug=True)
