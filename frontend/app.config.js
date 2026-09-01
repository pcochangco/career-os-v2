const baseConfig = require("./app.json").expo;

function googleIosUrlScheme(clientId) {
  const suffix = ".apps.googleusercontent.com";
  if (!clientId.endsWith(suffix)) {
    throw new Error("GOOGLE_IOS_CLIENT_ID must end with .apps.googleusercontent.com");
  }
  const identifier = clientId.slice(0, -suffix.length);
  if (!/^[A-Za-z0-9-]+$/.test(identifier)) {
    throw new Error("GOOGLE_IOS_CLIENT_ID is not a valid Google OAuth client ID");
  }
  return `com.googleusercontent.apps.${identifier}`;
}

module.exports = () => {
  const googleIosClientId = (process.env.GOOGLE_IOS_CLIENT_ID || "").trim();
  const plugins = [...(baseConfig.plugins || []), "expo-apple-authentication"];

  if (googleIosClientId) {
    plugins.push([
      "react-native-nitro-google-signin",
      { iosUrlScheme: googleIosUrlScheme(googleIosClientId) },
    ]);
  }

  return {
    ...baseConfig,
    ios: {
      ...baseConfig.ios,
      buildNumber: "1",
      usesAppleSignIn: true,
    },
    android: {
      ...baseConfig.android,
      versionCode: 1,
    },
    plugins,
  };
};
