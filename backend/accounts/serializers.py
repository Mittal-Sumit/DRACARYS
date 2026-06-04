from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

ALLOWED_DOMAIN = "ganitinc.com"


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        value = value.lower().strip()
        if not value.endswith(f"@{ALLOWED_DOMAIN}"):
            raise serializers.ValidationError(
                f"Only @{ALLOWED_DOMAIN} email addresses are allowed."
            )
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return User.objects.create_user(
            username=username,
            email=email,
            password=validated_data["password"],
        )
