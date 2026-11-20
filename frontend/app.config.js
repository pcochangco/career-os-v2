const { withPodfile } = require("expo/config-plugins");

const baseConfig = require("./app.json").expo;

// The Google Sign-In pods need modular headers to build. The library's plugin adds them, but it
// only runs with a Google iOS client ID; the native module is linked either way, so builds
// without an ID (local, simulator) add the same lines here.
const GOOGLE_SIGN_IN_PODS = [
  "  pod 'AppCheckCore', :modular_headers => true",
  "  pod 'GoogleUtilities', :modular_headers => true",
  "  pod 'RecaptchaInterop', :modular_headers => true",
].join("\n");

function withGoogleSignInPods(config) {
  return withPodfile(config, (podConfig) => {
    const podfile = podConfig.modResults.contents;
    if (!podfile.includes("pod 'AppCheckCore'")) {
      podConfig.modResults.contents = podfile.replace(
        /^(\s*config = use_native_modules)/m,
        `${GOOGLE_SIGN_IN_PODS}\n$1`,
      );
    }
    return podConfig;
  });
}

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
  const plugins = [
    ...(baseConfig.plugins || []),
    "expo-apple-authentication",
    "expo-status-bar",
  ];

  if (googleIosClientId) {
    plugins.push([
      "react-native-nitro-google-signin",
      { iosUrlScheme: googleIosUrlScheme(googleIosClientId) },
    ]);
  } else {
    plugins.push(withGoogleSignInPods);
  }

  return {
    ...baseConfig,
    owner: "careerosapps-team",
    extra: {
      ...(baseConfig.extra ?? {}),
      eas: {
        ...(baseConfig.extra?.eas ?? {}),
        projectId: "18d01b82-d04e-4a25-b2cc-3576122a4941",
      },
    },
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
