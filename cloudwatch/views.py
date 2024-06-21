from rest_framework.decorators import api_view, authentication_classes, permission_classes 
from rest_framework.response import Response
from rest_framework import status,generics
from cloudwatch.utils import get_time_interval
from .models import Log, LogCount
from .serializers import LogSerializer
from rest_framework.exceptions import ValidationError
import re
from django.db.models import Q
from .logs import save_log
from collections import defaultdict
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMinute, TruncHour, TruncDay
from datetime import timedelta, datetime


@api_view(['GET', 'POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def log_list(request):
    """
    View function for handling GET and POST requests to the log_list endpoint.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object.

    Raises:
        ValidationError: If a log with the same ingestionTime already exists.

    Description:
        This function handles GET and POST requests to the log_list endpoint.
        If the request method is GET, it retrieves logs based on the provided period query parameter.
        If the period parameter is provided, it calls the get_time_interval function to get the start and end times
        for the specified period. It then filters the Log objects based on the timestamp range.
        If the period parameter is not provided, it retrieves all Log objects.
        It serializes the logs using the LogSerializer and returns the serialized data in the response.

        If the request method is POST, it expects the request data to contain a valid log object.
        It validates the serialized data using the LogSerializer.
        If the data is valid, it checks if a log with the same ingestionTime already exists.
        If it does, it raises a ValidationError.
        If it doesn't exist, it saves the log object and calls the update_log_count function to update the log count.
        It returns the serialized data in the response with a status code of 201 (Created).
        If the data is not valid, it returns the serializer errors in the response with a status code of 400 (Bad Request).
    """
        
    if request.method == 'GET':
        print(timezone.LocalTimezone())
        period = request.query_params.get('period', None)
        if period:
            try:
                start_time, end_time = get_time_interval(period)
                logs = Log.objects.filter(timestamp__range=(start_time, end_time))
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            logs = Log.objects.all()

        serializer = LogSerializer(logs, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = LogSerializer(data=request.data)
        if serializer.is_valid():
            log_data = serializer.validated_data
            existing_logs = Log.objects.filter(ingestionTime=log_data['ingestionTime'])
            if existing_logs.exists():
                raise ValidationError("A log with the same ingestionTime already exists.")
            
            log = serializer.save()
            update_log_count(log)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def log_detail(request, pk):
    """
    View function for handling GET, PUT, PATCH, and DELETE requests to the log_detail endpoint.

    Parameters:
        request (HttpRequest): The HTTP request object.
        pk (int): The primary key of the log object.

    Returns:
        Response: The HTTP response object.

    Raises:
        ValidationError: If a log with the same ingestionTime already exists during a PUT or PATCH request.

    Description:
        This function handles GET, PUT, PATCH, and DELETE requests to the log_detail endpoint.
        If the request method is GET, it retrieves a log object based on the provided primary key.
        If the log object exists, it serializes it using the LogSerializer and returns the serialized data in the response.
        If the log object does not exist, it returns a 404 (Not Found) response.

        If the request method is PUT, it expects the request data to contain a valid log object.
        It validates the serialized data using the LogSerializer.
        If the data is valid, it updates the log object and calls the update_log_count function to update the log count.
        It returns the serialized data in the response.
        If the data is not valid, it returns the serializer errors in the response with a status code of 400 (Bad Request).

        If the request method is PATCH, it expects the request data to contain a valid partial log object.
        It validates the serialized data using the LogSerializer with partial=True.
        If the data is valid, it updates the log object and calls the update_log_count function to update the log count.
        It returns the serialized data in the response.
        If the data is not valid, it returns the serializer errors in the response with a status code of 400 (Bad Request).

        If the request method is DELETE, it deletes the log object.
        It returns a 204 (No Content) response.
    """
        
    try:
        log = Log.objects.get(pk=pk)
    except Log.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = LogSerializer(log)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = LogSerializer(log, data=request.data)
        if serializer.is_valid():
            log = serializer.save()
            update_log_count(log)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PATCH':
        serializer = LogSerializer(log, data=request.data, partial=True)
        if serializer.is_valid():
            log = serializer.save()
            update_log_count(log)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        log.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def log_count_list(request):
    """
    View function for handling GET requests to the log_count_list endpoint.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object containing the log counts.

    Description:
        This function handles GET requests to the log_count_list endpoint.
        It initializes the counts for INFO, ERROR, and WARN log messages.
        It retrieves all logs from the Log model.
        It loops through the logs and counts the occurrences of patterns
        '[INFO ]', '[ERROR]', and '[WARN ]' in the log message.
        It creates a dictionary with the counts and returns it in the response.
    """

    # Initialize counts
    info_count = 0
    error_count = 0
    warn_count = 0

    # Get all logs
    logs = Log.objects.all()

    # Loop through logs and count occurrences of patterns
    for log in logs:
        if re.search(r'\[INFO \]', log.message):
            info_count += 1
        if re.search(r'\[ERROR \]', log.message):
            error_count += 1
        if re.search(r'\[WARN \]', log.message):
            warn_count += 1

    # Create response
    log_counts = {
        'INFO': info_count,
        'ERROR': error_count,
        'WARN': warn_count
    }

    return Response(log_counts)


def update_log_count(log):
    """
    Updates the log count for a given log by counting the occurrences of different log levels in the log message.
    
    Parameters:
        log (Log): The log object for which the count needs to be updated.
        
    Returns:
        None
    """
    
    message = log.message
    info_count = len(re.findall(r'\[INFO \]', message))
    error_count = len(re.findall(r'\[ERROR \]', message))
    warn_count = len(re.findall(r'\[WARN \]', message))

    log_count, created = LogCount.objects.get_or_create(log=log)
    if not created:
        log_count.info_count = info_count
        log_count.error_count = error_count
        log_count.warn_count = warn_count
        log_count.save()


# @api_view(['GET'])
# def filter_logs(request):
#     """
#     View function for handling GET requests to the filter_logs endpoint.

#     Parameters:
#         request (HttpRequest): The HTTP request object.

#     Returns:
#         Response: The HTTP response object containing the filtered logs.

#     Description:
#         This function handles GET requests to the filter_logs endpoint.
#         It filters logs based on the 'log_level' query parameter.
#         Supported log levels are '[INFO ]', '[ERROR]', and '[WARN ]'.
#         It serializes the filtered logs using the LogSerializer and returns the serialized data in the response.
#     """
    
#     security_info = request.query_params.get('security_info', None)
#     if security_info not in ['INFO', 'ERROR', 'WARN']:
#         return Response({"error": "Invalid log level. Valid options are 'INFO', 'ERROR', and 'WARN'."}, status=status.HTTP_400_BAD_REQUEST)

#     security_info_pattern = f'\\[{security_info} \\]'
#     logs = Log.objects.filter(message__regex=security_info_pattern)

#     serializer = LogSerializer(logs, many=True)
#     return Response(serializer.data)



@api_view(["GET"])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def logs_views(request):
    if request.method == "GET":
        logs_data = save_log()
        serializer = LogSerializer(data=logs_data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response("Logs saved successfully", status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response("Method not allowed", status=status.HTTP_405_METHOD_NOT_ALLOWED)


class Logview(generics.ListCreateAPIView):
    queryset = Log.objects.all()
    serializer_class = LogSerializer

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def total_logs_count(request):
    """
    View function for handling GET requests to the total_logs_count endpoint.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object containing the total count of logs.
    """
    total_count = Log.objects.count()
    return Response({'total_logs_count': total_count})


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def recent_logs(request):
    """
    View function for handling GET requests to the recent_logs endpoint.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object containing the most recent 5 logs.
    """
    recent_logs = Log.objects.order_by('-timestamp')[:5]
    serializer = LogSerializer(recent_logs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def filter_logs(request):
    """
    View function for handling GET requests to filter logs based on multiple query parameters.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object containing the filtered logs.

    Description:
        This function handles GET requests to filter logs based on `logname`, `logstreamname`, `period`, and `securityinfo` query parameters.
        It retrieves the query parameters from the request, applies the necessary filters, and returns the filtered logs in the response.
    """
    logGroupName = request.query_params.get('logGroupName', None)
    logStreamName = request.query_params.get('logStreamName', None)
    period = request.query_params.get('period', None)
    securityinfo = request.query_params.get('securityinfo', None)

    filters = Q()

    if logGroupName:
        filters &= Q(logGroupName=logGroupName)
    if logStreamName:
        filters &= Q(logStreamName=logStreamName)
    if period:
        try:
            start_time, end_time = get_time_interval(period)
            filters &= Q(timestamp__range=(start_time, end_time))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    if securityinfo:
        if securityinfo not in ['INFO', 'ERROR', 'WARN']:
            return Response({"error": "Invalid securityinfo. Valid options are 'INFO', 'ERROR', and 'WARN'."}, status=status.HTTP_400_BAD_REQUEST)
        securityinfo_pattern = f'\\[{securityinfo} \\]'
        filters &= Q(message__regex=securityinfo_pattern)

    logs = Log.objects.filter(filters)
    serializer = LogSerializer(logs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def logs_grouped_by_group_and_stream(request):
    """
    View function for handling GET requests to retrieve logs grouped by logGroupName and logStreamName.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object containing the logGroupName and logStreamName grouped by logGroupName and logStreamName.
    """
    logs = Log.objects.all()
    logs_by_group_and_stream = defaultdict(set)

    for log in logs:
        logs_by_group_and_stream[log.logGroupName].add(log.logStreamName)

    response_data = []
    for group_name, streams in logs_by_group_and_stream.items():
        group_data = {
            "logGroupName": group_name,
            "logStreams": [{"logStreamName": stream_name} for stream_name in streams]
        }
        response_data.append(group_data)

    return Response(response_data)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def log_count_interval(request):
    """
    View function to get the count of logs in specified intervals.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        Response: The HTTP response object containing the count of logs in specified intervals.
    """
    interval_type = request.query_params.get('interval_type', 'last_week')
    now = timezone.now()
    print(now)
    
    if interval_type == 'last_hour':
        end_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=10)
        start_time = end_time - timedelta(hours=1)
        interval_delta = timedelta(minutes=5)
        truncate_function = TruncMinute
    elif interval_type == 'last_day':
        end_time = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=6,minutes=45)
        start_time = end_time - timedelta(days=1)
        interval_delta = timedelta(hours=1)
        truncate_function = TruncHour
    elif interval_type == 'previous_day':
        end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=1)
        interval_delta = timedelta(hours=1)
        truncate_function = TruncHour
    elif interval_type == 'last_week':
        end_of_last_week = now - timedelta(days=now.weekday() + 2)
        end_time = end_of_last_week.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_last_week = end_time - timedelta(days=6)
        start_time = start_of_last_week.replace(hour=0, minute=0, second=0, microsecond=0)
        interval_delta = timedelta(days=1)
        truncate_function = TruncDay
    elif interval_type == 'last_month':
        first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
        start_time = last_day_of_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = last_day_of_last_month.replace(hour=23, minute=59, second=59, microsecond=999999)
        interval_delta = timedelta(days=1)
        truncate_function = TruncDay
    else:
        return Response({"error": "Invalid interval type. Valid options are 'last_hour', 'last_day', 'previous_day', 'last_week', and 'last_month'."},
                        status=status.HTTP_400_BAD_REQUEST)
    print("Start-time: ",start_time)
    print("end-time: ",end_time)
    # Truncate timestamp to the specified interval and count logs
    logs = Log.objects.filter(timestamp__range=(start_time, end_time))
    logs = logs.annotate(interval=truncate_function('timestamp'))
    logs_count = logs.values('interval').annotate(count=Count('id')).order_by('interval')

    # Prepare response data with all intervals
    response_data = []
    interval_time = start_time

    while interval_time <= end_time:
        interval_end = interval_time + interval_delta
        count = Log.objects.filter(timestamp__range=(interval_time, interval_end)).count()
        # count = next((item['count'] for item in logs_count if item['interval'] == interval_time), 0)
        response_data.append({
            # 'interval_start': interval_time,
            'interval': interval_end,
            'count': count
        })
        interval_time += interval_delta

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def last_seven_days(request):
    current_date = datetime.now()

    last_week_log = []
    for i in range(1, 8):
        previous_day = current_date - timedelta(days=i)
        start_date = previous_day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = previous_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        log_count = Log.objects.filter(timestamp__range=(start_date, end_date)).count()
        formatted_date = previous_day.astimezone().isoformat(timespec="milliseconds")
        log_entry = {"timestamp": formatted_date, "log_count": log_count}
        last_week_log.append(log_entry)

    last_week_log.reverse()
    return Response(last_week_log)
