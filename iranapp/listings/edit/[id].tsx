// app/listing/edit/[id].tsx
import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, router } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { API } from "../../utils/_config/api";

type Listing = {
  id: number;
  title: string;
  city: string;
  state: string;
  price: string;
  description: string | null;
  contact_info: string;
};

export default function EditListingScreen() {
  const { id } = useLocalSearchParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [title, setTitle] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [price, setPrice] = useState("");
  const [contact, setContact] = useState("");
  const [description, setDescription] = useState("");
  const [selectedImage, setSelectedImage] = useState<ImagePicker.ImagePickerAsset | null>(null);

  // گرفتن اطلاعات فعلی آگهی
  useEffect(() => {
    const fetchListing = async () => {
      try {
        const res = await fetch(`${API.LISTINGS}${id}/`);
        const data: Listing = await res.json();
        setTitle(data.title);
        setCity(data.city);
        setState(data.state);
        setPrice(String(data.price));
        setContact(data.contact_info);
        setDescription(data.description || "");
      } catch (err) {
        console.log("FETCH LISTING ERROR:", err);
        Alert.alert("Error", "مشکل در خواندن اطلاعات آگهی.");
      } finally {
        setLoading(false);
      }
    };

    fetchListing();
  }, [id]);

  const pickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("Permission required", "اجازه دسترسی به گالری لازم است.");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      setSelectedImage(result.assets[0]);
    }
  };

  const handleSave = async () => {
    if (!title || !city || !state || !price || !contact) {
      Alert.alert("Error", "همه فیلدهای اصلی (عنوان، شهر، ایالت، قیمت، تماس) لازم است.");
      return;
    }

    setSaving(true);

    try {
      // 1) آپدیت خود آگهی
      const res = await fetch(`${API.LISTINGS}${id}/`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title,
          city,
          state,
          price,
          contact_info: contact,
          description,
        }),
      });

      if (!res.ok) {
        console.log("UPDATE ERROR STATUS:", res.status);
        Alert.alert("Error", "ویرایش آگهی موفق نبود.");
        setSaving(false);
        return;
      }

      // 2) اگر عکس جدید انتخاب شده، آن را هم آپلود کن
      if (selectedImage) {
        const formData = new FormData();
        formData.append("listing_id", String(id));
        formData.append("image", {
          // @ts-ignore
          uri: selectedImage.uri,
          name: "listing.jpg",
          type: "image/jpeg",
        });

        const imgRes = await fetch(`${API.LISTINGS}upload-image/`, {
          method: "POST",
          body: formData,
          // مهم: هدر Content-Type را نگذار؛ خودش multipart می‌سازد
        });

        if (!imgRes.ok) {
          console.log("UPLOAD IMAGE ERROR STATUS:", imgRes.status);
          Alert.alert("Warning", "آگهی ذخیره شد ولی آپلود عکس جدید ناموفق بود.");
        }
      }

      Alert.alert("Success", "آگهی با موفقیت ویرایش شد.", [
        {
          text: "OK",
          onPress: () => {
            router.back(); // برگرد به صفحهٔ قبلی (جزئیات آگهی)
          },
        },
      ]);
    } catch (err) {
      console.log("SAVE ERROR:", err);
      Alert.alert("Error", "خطا در ارتباط با سرور.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <ActivityIndicator size="large" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={styles.container}>
          <Text style={styles.title}>Edit listing</Text>

          <Text style={styles.label}>Title</Text>
          <TextInput
            style={styles.input}
            value={title}
            onChangeText={setTitle}
            placeholder="Room for rent..."
          />

          <Text style={styles.label}>City</Text>
          <TextInput
            style={styles.input}
            value={city}
            onChangeText={setCity}
            placeholder="Los Angeles..."
          />

          <Text style={styles.label}>State</Text>
          <TextInput
            style={styles.input}
            value={state}
            onChangeText={setState}
            placeholder="California..."
          />

          <Text style={styles.label}>Price (USD)</Text>
          <TextInput
            style={styles.input}
            value={price}
            onChangeText={setPrice}
            keyboardType="numeric"
            placeholder="1500"
          />

          <Text style={styles.label}>Contact info</Text>
          <TextInput
            style={styles.input}
            value={contact}
            onChangeText={setContact}
            placeholder="Phone or email"
          />

          <Text style={styles.label}>Description (optional)</Text>
          <TextInput
            style={[styles.input, { height: 80, textAlignVertical: "top" }]}
            value={description}
            onChangeText={setDescription}
            multiline
            placeholder="Write details about the room..."
          />

          <TouchableOpacity style={styles.imageButton} onPress={pickImage}>
            <Text style={styles.imageButtonText}>
              {selectedImage ? "Change image (optional)" : "Select new image (optional)"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.saveButton, saving && { opacity: 0.6 }]}
            onPress={handleSave}
            disabled={saving}
          >
            {saving ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.saveButtonText}>Save changes</Text>
            )}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#f2f2f2",
  },
  container: {
    padding: 16,
    paddingBottom: 32,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    marginTop: 12,
    marginBottom: 4,
  },
  input: {
    backgroundColor: "#fff",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
  },
  imageButton: {
    marginTop: 20,
    backgroundColor: "#ddd",
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  imageButtonText: {
    fontSize: 14,
    fontWeight: "500",
  },
  saveButton: {
    marginTop: 24,
    backgroundColor: "#007AFF",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  saveButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
