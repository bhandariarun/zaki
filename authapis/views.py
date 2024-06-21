from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, authentication_classes, permission_classes 
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer
from .models import User
from django.contrib.auth.hashers import make_password


@api_view(['POST'])
def login(request):
    """
    Logs in a user with the provided username and password.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object containing the login status, success message, and token if successful.
                  If the username or password is missing, returns a 400 error with a message.
                  If the username is less than 5 characters, returns a 400 error with a message.
                  If the user does not exist or the password is incorrect, returns a 404 error with a message.

    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    # Check if both username and password are provided
    if username is None or password is None:
        return Response({'message': 'Please provide both username and password',
                         'success': False},
                        status=400)
    
    # Validate that the username is greater than 4 characters
    if len(username) < 5:
        return Response({'message': 'Username must be atleast of 5 characters',
                         'success': False},
                        status=400)
    
    user = User.objects.filter(username=username).first()
    
    # Check if the user exists
    if not user:
        return Response({'message': 'Invalid Credentials',
                         'success': False},
                        status=404)
    
    # Check if the password is correct
    if not user.check_password(password):
        return Response({'message': 'Invalid Credentials',
                         'success': False},
                        status=404)
    
    # Generate or get the existing token for the user
    token, _ = Token.objects.get_or_create(user=user)
    
    return Response({'message': 'Login successful',
                     'success': True,
                     'token': token.key})


@api_view(['POST'])
def signup(request):
    """
    Creates a new user account with the provided username and password.

    Parameters:
        request (HttpRequest): The HTTP request object containing the user data.

    Returns:
        Response: The HTTP response object containing the token and user data if successful.
                  If the username is not provided or is less than 5 characters, returns a 400 error with a message.
    """
    # Extract the username from the request data
    username = request.data.get('username')
    
    # Check if the username is provided and is greater than 5 characters
    if username is None or len(username) < 5:
        return Response({'message': 'Username must be atleast of 5 characters',
                         'success': False},
                        status=400)
    
    serializer = UserSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    
    return Response({"token": token.key, "user": serializer.data}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def testtoken(request):
    """
    A view function that handles GET requests to the testtoken endpoint.
    
    This function is decorated with `@api_view(['GET'])` to indicate that it handles GET requests.
    It is also decorated with `@authentication_classes([SessionAuthentication,TokenAuthentication])`
    to specify that both session-based authentication and token-based authentication are required for accessing this endpoint.
    The `@permission_classes([IsAuthenticated])` decorator ensures that the user making the request is authenticated.
    
    Parameters:
        request (HttpRequest): The HTTP request object.
    
    Returns:
        Response: The HTTP response object containing the message "passed for {username}" where {username} is the username of the authenticated user.
    """
    user = request.user
    user_details = {
        'username': user.username,
        'email': user.email,
        'success': True
    }
    return Response(user_details)


@api_view(['PATCH'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_user(request):
    """
    Updates the username, email, or password of the authenticated user.

    Parameters:
        request (HttpRequest): The HTTP request object containing the new username, email, or password.

    Returns:
        Response: The HTTP response object containing the updated user data or an error message.
    """
    user = request.user
    data = request.data
    response_data = {}
    
    # Update username if provided
    new_username = data.get('username')
    if new_username:
        if len(new_username) < 5:
            return Response({'message': 'Username must be at least 5 characters', 'success': False}, status=400)
        user.username = new_username
        response_data['username'] = new_username

    # Update email if provided
    new_email = data.get('email')
    if new_email:
        if not new_email.strip():
            return Response({'message': 'Invalid email', 'success': False}, status=400)
        user.email = new_email
        response_data['email'] = new_email

    # Update password if provided
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    if current_password and new_password:
        if not user.check_password(current_password):
            return Response({'message': 'Current password is incorrect', 'success': False}, status=400)
        if len(new_password) < 8:
            return Response({'message': 'New password must be at least 8 characters', 'success': False}, status=400)
        user.password = make_password(new_password)
        response_data['password'] = 'Password updated successfully'

    user.save()
    serializer = UserSerializer(user)
    response_data.update(serializer.data)
    return Response({"user": response_data, "message": "User updated successfully"}, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logs out the user by deleting the token associated with the user.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object containing the success message and status code.
    """
    token = request.auth
    token.delete()
    return Response({'message': 'Logged out successfully', 'success': True}, status=200)
