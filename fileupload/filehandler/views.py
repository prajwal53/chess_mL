
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import UploadFileForm
from .models import UploadedFile
from wsgiref.util import FileWrapper
from django.shortcuts import get_object_or_404
import mimetypes
import os
from django.http import HttpResponseBadRequest
import chess.pgn
import chess.engine

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            player_color = request.POST.get('player_color', 'white')  # Default to white if not specified
            uploaded_file = form.save(commit=False)
            uploaded_file.player_color = player_color
            uploaded_file.save()
            print("File Saved Successfully:", uploaded_file.file.name)
            return redirect('upload_success')
        else:
            print("Form is not valid:", form.errors)
            return HttpResponseBadRequest("Form submission failed. Please check the form errors.")
    else:
        form = UploadFileForm()
    return render(request, 'filehandler/upload.html', {'form': form})

def analyze_pgn_and_get_results(pgn_file, player_to_analyze):
    beginner_threshold = 50
    intermediate_threshold = 20
    expert_threshold = 10

    max_cpl = 1000  # Assume the maximum CPL observed in the dataset is 1000

    with open(pgn_file) as file:
        game = chess.pgn.read_game(file)
        
        if game is None:
            print("No game found in the PGN file.")
            return
        
        total_games = 1  # Only one game is being analyzed
        total_moves = 0
        total_cpl = 0

        engine = chess.engine.SimpleEngine.popen_uci("C:/Users/PRAJWAL/Downloads/stockfish-windows-x86-64/stockfish/stockfish-windows-x86-64.exe",timeout=30)

        board = game.board()
        for move in game.mainline_moves():
            board.push(move)
            
            # Check if the move belongs to the specified player
            if (player_to_analyze == "white" and board.turn == chess.WHITE) or \
               (player_to_analyze == "black" and board.turn == chess.BLACK):
                total_moves += 1  # Increment total moves only for the specified player

                # Analyze the position after each move
                info = engine.analyse(board, chess.engine.Limit(time=1.0))

                # Check if the score is not None before adding it
                if info["score"].relative is not None and info["score"].relative.score() is not None:
                    total_cpl += abs(info["score"].relative.score())  # Absolute value of CPL

        engine.quit()

    average_cpl = total_cpl / total_moves if total_moves > 0 else 0
    scaled_cpl = (average_cpl / max_cpl) * 100

    if scaled_cpl > beginner_threshold:
        category = "Beginner"
    elif scaled_cpl > intermediate_threshold:
        category = "Intermediate"
    elif scaled_cpl > expert_threshold:
        category = "Expert"
    else:
        category = "Professional"

    
    learning_resources = {
        "Beginner": ["Chess Basics Tutorial", "Pawn Structure Strategies", "Opening Principles"],
        "Intermediate": ["Tactics Training", "Middle Game Planning", "Endgame Essentials"],
        "Expert": ["Advanced Tactics and Combinations", "Strategic Planning", "Endgame Mastery"],
        "Professional": ["Grandmaster Game Analysis", "Advanced Opening Theory", "Positional Sacrifices"]
    }

    return {
        "total_games": total_games,
        "total_moves": total_moves,
        "average_cpl": scaled_cpl,
        "category": category,
        "learning_resources": learning_resources.get(category, [])
    }

def download_file(request):
    latest_file = UploadedFile.objects.last()
    analysis_results = None
    
    # Perform analysis if a file exists
    if latest_file:
        pgn_file_path = latest_file.file.path
        analysis_results = analyze_pgn_and_get_results(pgn_file_path, player_to_analyze=latest_file.player_color)
        print("Analysis Results:", analysis_results)

    return render(request, 'filehandler/download.html', {'latest_file': latest_file, 'analysis_results': analysis_results})

def download_pdf(request, file_id):
    uploaded_file = get_object_or_404(UploadedFile, id=file_id)
    
    # Get the player's category from the request parameters
    category = request.GET.get('category')
    
    # Determine the appropriate PDF file based on the player's category
    pdf_file_path = None
    if category:
        pdf_folder = os.path.join(os.path.dirname(__file__), 'resources')  # Get the path to the resources folder
        if category == 'Beginner':
            pdf_file_path = os.path.join(pdf_folder, 'Beginners Guide.pdf')
        elif category == 'Intermediate':
            pdf_file_path = os.path.join(pdf_folder, 'INTERMEDIATE Guide.pdf')
        elif category == 'Expert':
            pdf_file_path = os.path.join(pdf_folder, 'EXPERT Guide.pdf')
        elif category == 'Professional':
            pdf_file_path = os.path.join(pdf_folder, 'Professional Guide.pdf')

    if pdf_file_path and os.path.exists(pdf_file_path):
        # Open and serve the PDF file
        with open(pdf_file_path, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_file_path)}"'
            return response
    else:
        # Return an error response if PDF file path is not found
        return HttpResponseBadRequest("PDF file not found for the player's category.")

def upload_success(request):
    return render(request, 'filehandler/upload_success.html')