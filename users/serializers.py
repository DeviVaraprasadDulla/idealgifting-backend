from django.contrib.auth.models import User
from rest_framework import serializers


from django.contrib.auth.models import User
from rest_framework import serializers


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password"]

    def create(self, validated_data):
        email = validated_data["email"]

        if User.objects.filter(username=email).exists():
            raise serializers.ValidationError({"email": "Email already exists"})

        user = User.objects.create_user(
            username=email,   # 🔥 email as username
            email=email,
            password=validated_data["password"],
        )
        return user
